"""
OCR Handler Module
Handles text extraction from images using EasyOCR
"""

import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

import numpy as np
from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OCR_LANGUAGES, OCR_GPU, MIN_CONFIDENCE, LOG_FORMAT, LOG_DATE_FORMAT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)


class OCRHandler:
    """Handles OCR text extraction with confidence scoring"""

    def __init__(self, languages: List[str] = None, use_gpu: bool = None):
        """
        Initialize EasyOCR reader

        Args:
            languages: List of language codes (default: ['en'])
            use_gpu: Whether to use GPU acceleration (default: False)
        """
        languages = languages or OCR_LANGUAGES
        use_gpu = use_gpu if use_gpu is not None else OCR_GPU

        logger.info("=" * 50)
        logger.info("INITIALIZING OCR ENGINE")
        logger.info("=" * 50)
        logger.info(f"  Languages: {languages}")
        logger.info(f"  GPU: {use_gpu}")
        logger.info("  (First run downloads models - may take 30-60s)")

        start_time = time.time()

        # Import and initialize EasyOCR
        import easyocr
        self.reader = easyocr.Reader(languages, gpu=use_gpu)

        duration = time.time() - start_time
        logger.info(f"  Initialization time: {duration:.1f}s")
        logger.info("  OCR Engine ready")
        logger.info("=" * 50)

    def extract_text_from_image(
        self,
        image: Image.Image,
        detail: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Extract all text from an image

        Args:
            image: PIL Image object
            detail: 0 for simple output, 1 for detailed with boxes

        Returns:
            List of detection results with text, confidence, and bounding boxes
        """
        logger.info("Extracting text from image")
        logger.info(f"  Image size: {image.size}")

        start_time = time.time()

        # Convert PIL Image to numpy array
        img_array = np.array(image)

        # Run OCR
        results = self.reader.readtext(img_array, detail=detail)

        duration = time.time() - start_time
        logger.info(f"  Found {len(results)} text regions")
        logger.info(f"  Duration: {duration*1000:.0f}ms")

        # Parse results
        detections = []
        for result in results:
            if detail == 1:
                bbox, text, confidence = result
                detections.append({
                    'text': text,
                    'confidence': confidence,
                    'bbox': bbox,
                    'center': self._get_bbox_center(bbox)
                })
            else:
                detections.append({
                    'text': result,
                    'confidence': 1.0,
                    'bbox': None,
                    'center': None
                })

        return detections

    def extract_text(
        self,
        image: Image.Image,
        region: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract text from a specific region

        Args:
            image: PIL Image object (full screenshot)
            region: Dict with {name, x, y, width, height}

        Returns:
            Dict with {text, confidence, region_name, raw_detections}
        """
        logger.info(f"Extracting text from region: '{region['name']}'")
        logger.info(f"  Region: ({region['x']}, {region['y']}, {region['width']}x{region['height']})")

        # Validate region bounds
        img_width, img_height = image.size
        x = max(0, region['x'])
        y = max(0, region['y'])
        x2 = min(img_width, x + region['width'])
        y2 = min(img_height, y + region['height'])

        if x >= x2 or y >= y2:
            logger.error(f"  Invalid region bounds!")
            return {
                'text': '',
                'confidence': 0,
                'region_name': region['name'],
                'raw_detections': [],
                'error': 'Invalid region bounds'
            }

        # Crop image to region
        cropped = image.crop((x, y, x2, y2))
        logger.info(f"  Cropped size: {cropped.size}")

        # Convert to numpy array
        img_array = np.array(cropped)

        # Run OCR
        start_time = time.time()
        results = self.reader.readtext(img_array)
        duration = time.time() - start_time

        logger.info(f"  OCR duration: {duration*1000:.0f}ms")

        if not results:
            logger.warning(f"  No text detected in region '{region['name']}'")
            return {
                'text': '',
                'confidence': 0,
                'region_name': region['name'],
                'raw_detections': []
            }

        # Combine all detected text
        texts = []
        confidences = []
        raw_detections = []

        for bbox, text, conf in results:
            texts.append(text)
            confidences.append(conf)
            raw_detections.append({
                'text': text,
                'confidence': conf,
                'bbox': bbox
            })
            logger.info(f"    Detected: '{text}' (conf: {conf*100:.1f}%)")

        combined_text = ' '.join(texts)
        avg_confidence = sum(confidences) / len(confidences)

        logger.info(f"  Combined text: '{combined_text}'")
        logger.info(f"  Avg confidence: {avg_confidence*100:.1f}%")

        if avg_confidence < MIN_CONFIDENCE:
            logger.warning(f"  LOW CONFIDENCE: {avg_confidence*100:.1f}% < {MIN_CONFIDENCE*100:.0f}%")

        result = {
            'text': str(combined_text),
            'confidence': float(avg_confidence),
            'region_name': str(region['name']),
            'raw_detections': self._convert_to_json_serializable(raw_detections)
        }
        return result

    def extract_all_regions(
        self,
        image: Image.Image,
        regions: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract text from all defined regions

        Args:
            image: PIL Image object (full screenshot)
            regions: List of region dicts [{name, x, y, width, height}, ...]

        Returns:
            Dict mapping region names to extraction results
        """
        logger.info("=" * 50)
        logger.info(f"EXTRACTING FROM {len(regions)} REGIONS")
        logger.info("=" * 50)

        results = {}
        total_start = time.time()

        for i, region in enumerate(regions, 1):
            logger.info(f"\n[Region {i}/{len(regions)}]")
            result = self.extract_text(image, region)
            results[region['name']] = result

        total_duration = time.time() - total_start

        logger.info("\n" + "=" * 50)
        logger.info("EXTRACTION SUMMARY")
        logger.info("=" * 50)
        logger.info(f"  Regions processed: {len(regions)}")
        logger.info(f"  Total duration: {total_duration*1000:.0f}ms")

        for name, result in results.items():
            status = "OK" if result['confidence'] >= MIN_CONFIDENCE else "LOW"
            logger.info(f"  {name}: '{result['text'][:30]}...' [{status}]")

        logger.info("=" * 50)

        # Ensure all results are JSON-serializable
        return self._convert_to_json_serializable(results)

    def find_text_on_screen(
        self,
        image: Image.Image,
        search_text: str,
        case_sensitive: bool = False,
        min_confidence: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """
        Find specific text on screen and return its location

        Args:
            image: PIL Image to search
            search_text: Text to find
            case_sensitive: Whether to match case
            min_confidence: Minimum confidence threshold

        Returns:
            Dict with {text, confidence, bbox, center} or None if not found
        """
        logger.info(f"Searching for text: '{search_text}'")

        # Get all text from image
        detections = self.extract_text_from_image(image)

        search = search_text if case_sensitive else search_text.lower()

        for detection in detections:
            detected_text = detection['text'] if case_sensitive else detection['text'].lower()

            if search in detected_text and detection['confidence'] >= min_confidence:
                logger.info(f"  Found: '{detection['text']}' at {detection['center']}")
                logger.info(f"  Confidence: {detection['confidence']*100:.1f}%")
                return detection

        logger.warning(f"  Text '{search_text}' not found")
        return None

    def find_all_text_matches(
        self,
        image: Image.Image,
        search_text: str,
        case_sensitive: bool = False,
        min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find all instances of specific text on screen

        Args:
            image: PIL Image to search
            search_text: Text to find
            case_sensitive: Whether to match case
            min_confidence: Minimum confidence threshold

        Returns:
            List of matching detections
        """
        logger.info(f"Searching for all instances of: '{search_text}'")

        detections = self.extract_text_from_image(image)
        matches = []

        search = search_text if case_sensitive else search_text.lower()

        for detection in detections:
            detected_text = detection['text'] if case_sensitive else detection['text'].lower()

            if search in detected_text and detection['confidence'] >= min_confidence:
                matches.append(detection)
                logger.info(f"  Match: '{detection['text']}' at {detection['center']}")

        logger.info(f"  Total matches: {len(matches)}")
        return matches

    def _get_bbox_center(self, bbox) -> tuple:
        """Calculate center point of bounding box"""
        if bbox is None:
            return None

        # bbox is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
        x_coords = [point[0] for point in bbox]
        y_coords = [point[1] for point in bbox]

        center_x = int(sum(x_coords) / len(x_coords))
        center_y = int(sum(y_coords) / len(y_coords))

        return (center_x, center_y)

    def _convert_to_json_serializable(self, data):
        """Convert numpy types to native Python types for JSON serialization"""
        if isinstance(data, dict):
            return {k: self._convert_to_json_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._convert_to_json_serializable(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(self._convert_to_json_serializable(item) for item in data)
        elif hasattr(data, 'item'):  # numpy types have .item() method
            return data.item()
        elif isinstance(data, (np.integer, np.floating)):
            return float(data)
        elif isinstance(data, np.ndarray):
            return data.tolist()
        return data

    def get_data_as_dict(
        self,
        extraction_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Convert extraction results to simple key-value dict

        Args:
            extraction_results: Results from extract_all_regions()

        Returns:
            Dict mapping region names to extracted text values
        """
        return {
            name: result['text']
            for name, result in extraction_results.items()
        }
