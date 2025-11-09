# tests/curator/test_image_utils_dry_run.py
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".curator/lib"))

from image_utils import ImageLocalizer
from dry_run_utils import ImageValidator


def test_image_localizer_uses_validator_when_provided():
    """ImageLocalizer should use validator instead of downloading when provided."""
    # Mock Supabase client
    mock_supabase = Mock()

    # Create validator
    validator = ImageValidator()

    # Create localizer with validator
    localizer = ImageLocalizer(mock_supabase, image_validator=validator)

    # Mock validation result
    with patch.object(validator, 'validate_image') as mock_validate:
        mock_validate.return_value = {
            "url": "https://example.com/test.jpg",
            "accessible": True,
            "status_code": 200
        }

        # Should use validator, not download
        image_url, thumbnail_url = localizer.localize_image(
            "https://example.com/test.jpg",
            "test-entity-id"
        )

    # Should return mock URLs
    assert "[would localize from" in image_url
    assert thumbnail_url is None

    # Should have called validator
    mock_validate.assert_called_once()
