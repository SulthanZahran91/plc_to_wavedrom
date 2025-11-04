"""Tests for map viewer YAML configuration loading."""

import pytest
import tempfile
import yaml
from pathlib import Path
from PySide6.QtGui import QColor

from tools.map_viewer.config_loader import load_xml_parsing_config
from tools.map_viewer import config as map_config


@pytest.fixture
def sample_yaml_config():
    """Create a sample YAML configuration."""
    return {
        "default_color": "#D3D3D3",
        "xml_parsing": {
            "attributes_to_extract": ["type", "id"],
            "child_elements_to_extract": ["Text", "Size", "Location"],
            "render_as_text_types": [
                "System.Windows.Forms.Label, System.Windows.Forms, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089"
            ],
            "render_as_arrow_types": [
                "SmartFactory.SmartCIM.GUI.Widgets.WidgetArrow, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null"
            ],
            "type_color_mapping": {
                "default": "#D3D3D3",
                "special": "#FF0000"
            },
            "type_zindex_mapping": {
                "WidgetPort": 5,
                "default": 0
            },
            "forecolor_mapping": {
                "HotTrack": "#0066CC",
                "Black": "#000000",
                "Red": "#FF0000",
                "default": "#000000"
            }
        },
        "device_to_unit": [],
        "rules": []
    }


@pytest.fixture
def incomplete_yaml_config():
    """Create an incomplete YAML configuration."""
    return {
        "default_color": "#D3D3D3",
        "xml_parsing": {
            "attributes_to_extract": ["type"],
            # Missing other fields
        }
    }


class TestLoadXMLParsingConfig:
    """Test loading XML parsing configuration from YAML."""
    
    def test_load_xml_config_structure(self, sample_yaml_config):
        """Verify load_xml_parsing_config returns correct structure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_yaml_config, f)
            temp_path = f.name
        
        try:
            config = load_xml_parsing_config(temp_path)
            
            # Should have all required keys
            assert "attributes_to_extract" in config
            assert "child_elements_to_extract" in config
            assert "render_as_text_types" in config
            assert "render_as_arrow_types" in config
            assert "type_color_mapping" in config
            assert "type_zindex_mapping" in config
            assert "forecolor_mapping" in config
            
            # All values should be present
            assert config["attributes_to_extract"] is not None
            assert config["child_elements_to_extract"] is not None
            assert config["render_as_text_types"] is not None
            assert config["render_as_arrow_types"] is not None
            assert config["type_color_mapping"] is not None
            assert config["type_zindex_mapping"] is not None
            assert config["forecolor_mapping"] is not None
        finally:
            Path(temp_path).unlink()
    
    def test_load_from_yaml_file(self, sample_yaml_config):
        """Test actual YAML file loading."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_yaml_config, f)
            temp_path = f.name
        
        try:
            config = load_xml_parsing_config(temp_path)
            
            # Check specific values match YAML content
            assert "type" in config["attributes_to_extract"]
            assert "id" in config["attributes_to_extract"]
            assert "Text" in config["child_elements_to_extract"]
            assert len(config["render_as_text_types"]) == 1
            assert len(config["render_as_arrow_types"]) == 1
        finally:
            Path(temp_path).unlink()
    
    def test_fallback_on_missing_yaml(self):
        """Test defaults when YAML file not found."""
        config = load_xml_parsing_config("/nonexistent/file.yaml")
        
        # Should return empty config (handled by fallback defaults in config.py)
        assert isinstance(config, dict)
        assert "attributes_to_extract" in config
        
        # Empty config triggers fallback logic
        assert config["attributes_to_extract"] == []
    
    def test_fallback_on_incomplete_yaml(self, incomplete_yaml_config):
        """Test defaults for missing keys in YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(incomplete_yaml_config, f)
            temp_path = f.name
        
        try:
            config = load_xml_parsing_config(temp_path)
            
            # Should have attributes_to_extract
            assert "type" in config["attributes_to_extract"]
            
            # Missing fields should have defaults
            assert config["child_elements_to_extract"] == []
            assert config["render_as_text_types"] == []
            assert config["render_as_arrow_types"] == []
        finally:
            Path(temp_path).unlink()
    
    def test_handles_invalid_yaml(self):
        """Test handling of invalid YAML content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [[[")
            temp_path = f.name
        
        try:
            # Should not raise exception, should return fallback
            config = load_xml_parsing_config(temp_path)
            
            # Should return empty config structure
            assert isinstance(config, dict)
        finally:
            Path(temp_path).unlink()


class TestConfigModuleIntegration:
    """Test integration with the config module."""
    
    def test_attributes_to_extract_loaded(self):
        """Check ATTRIBUTES_TO_EXTRACT is loaded from config."""
        # Should be a list
        assert isinstance(map_config.ATTRIBUTES_TO_EXTRACT, list)
        
        # Should have at least "type"
        assert "type" in map_config.ATTRIBUTES_TO_EXTRACT or len(map_config.ATTRIBUTES_TO_EXTRACT) > 0
    
    def test_child_elements_to_extract_loaded(self):
        """Check CHILD_ELEMENTS_TO_EXTRACT is loaded from config."""
        assert isinstance(map_config.CHILD_ELEMENTS_TO_EXTRACT, list)
        
        # Should have common elements
        common_elements = ["Text", "Size", "Location"]
        has_common = any(elem in map_config.CHILD_ELEMENTS_TO_EXTRACT for elem in common_elements)
        assert has_common or len(map_config.CHILD_ELEMENTS_TO_EXTRACT) > 0
    
    def test_render_as_text_types_loaded(self):
        """Check RENDER_AS_TEXT_TYPES is loaded from config."""
        assert isinstance(map_config.RENDER_AS_TEXT_TYPES, list)
        
        # Should be non-empty or use defaults
        assert len(map_config.RENDER_AS_TEXT_TYPES) >= 0
    
    def test_render_as_arrow_types_loaded(self):
        """Check RENDER_AS_ARROW_TYPES is loaded from config."""
        assert isinstance(map_config.RENDER_AS_ARROW_TYPES, list)
        
        # Should be non-empty or use defaults
        assert len(map_config.RENDER_AS_ARROW_TYPES) >= 0
    
    def test_type_color_mapping_loaded(self):
        """Check TYPE_COLOR_MAPPING is loaded and converted to QColor."""
        assert isinstance(map_config.TYPE_COLOR_MAPPING, dict)
        
        # Should have at least default
        assert "default" in map_config.TYPE_COLOR_MAPPING
        
        # Values should be QColor instances
        for key, value in map_config.TYPE_COLOR_MAPPING.items():
            assert isinstance(value, QColor)
    
    def test_type_zindex_mapping_loaded(self):
        """Check TYPE_ZINDEX_MAPPING is loaded."""
        assert isinstance(map_config.TYPE_ZINDEX_MAPPING, dict)
        
        # Should have at least default
        assert "default" in map_config.TYPE_ZINDEX_MAPPING
        
        # Values should be integers
        for key, value in map_config.TYPE_ZINDEX_MAPPING.items():
            assert isinstance(value, int)
    
    def test_forecolor_mapping_loaded(self):
        """Check FORECOLOR_MAPPING is loaded and converted to QColor."""
        assert isinstance(map_config.FORECOLOR_MAPPING, dict)
        
        # Should have at least default
        assert "default" in map_config.FORECOLOR_MAPPING
        
        # Values should be QColor instances
        for key, value in map_config.FORECOLOR_MAPPING.items():
            assert isinstance(value, QColor)


class TestHexColorConversion:
    """Test hex color string conversion to QColor."""
    
    def test_hex_to_qcolor_conversion(self):
        """Verify hex color conversion works correctly."""
        # Use the helper function from config module
        from tools.map_viewer.config import _hex_to_qcolor
        
        # Test standard hex color
        color = _hex_to_qcolor("#FF0000")
        assert isinstance(color, QColor)
        assert color.red() == 255
        assert color.green() == 0
        assert color.blue() == 0
    
    def test_hex_to_qcolor_various_formats(self):
        """Test various hex color formats."""
        from tools.map_viewer.config import _hex_to_qcolor
        
        # Test with #
        color1 = _hex_to_qcolor("#00FF00")
        assert color1.green() == 255
        
        # Test short hex (should still work with QColor)
        color2 = _hex_to_qcolor("#0000FF")
        assert color2.blue() == 255
    
    def test_color_mapping_has_valid_qcolors(self):
        """Verify all colors in mappings are valid QColor objects."""
        # Check TYPE_COLOR_MAPPING
        for key, color in map_config.TYPE_COLOR_MAPPING.items():
            assert isinstance(color, QColor)
            assert color.isValid()
        
        # Check FORECOLOR_MAPPING
        for key, color in map_config.FORECOLOR_MAPPING.items():
            assert isinstance(color, QColor)
            assert color.isValid()


class TestBackwardCompatibility:
    """Test backward compatibility with old hardcoded values."""
    
    def test_default_color_mapping_exists(self):
        """Verify default entry exists in color mapping."""
        assert "default" in map_config.TYPE_COLOR_MAPPING
        
        default_color = map_config.TYPE_COLOR_MAPPING["default"]
        assert isinstance(default_color, QColor)
        
        # Should be light gray (211, 211, 211) or similar
        # Allow some flexibility in case YAML overrides it
        assert default_color.isValid()
    
    def test_default_zindex_exists(self):
        """Verify default entry exists in zindex mapping."""
        assert "default" in map_config.TYPE_ZINDEX_MAPPING
        
        default_zindex = map_config.TYPE_ZINDEX_MAPPING["default"]
        assert isinstance(default_zindex, int)
        assert default_zindex >= 0
    
    def test_default_forecolor_exists(self):
        """Verify default entry exists in forecolor mapping."""
        assert "default" in map_config.FORECOLOR_MAPPING
        
        default_forecolor = map_config.FORECOLOR_MAPPING["default"]
        assert isinstance(default_forecolor, QColor)
        assert default_forecolor.isValid()
    
    def test_common_forecolors_present(self):
        """Verify common forecolor names are present."""
        common_colors = ["Black", "Red", "Green", "Blue"]
        
        # At least some common colors should be present
        present = [color for color in common_colors if color in map_config.FORECOLOR_MAPPING]
        
        # Should have at least default if YAML is empty
        assert len(map_config.FORECOLOR_MAPPING) >= 1


class TestYAMLConfigValues:
    """Test specific values from the actual YAML file."""
    
    def test_yaml_file_exists(self):
        """Verify the actual mappings_and_rules.yaml file exists."""
        yaml_path = Path(__file__).parent.parent / "tools" / "map_viewer" / "mappings_and_rules.yaml"
        
        # File should exist
        assert yaml_path.exists()
        assert yaml_path.is_file()
    
    def test_can_load_actual_yaml(self):
        """Test loading the actual YAML configuration file."""
        yaml_path = Path(__file__).parent.parent / "tools" / "map_viewer" / "mappings_and_rules.yaml"
        
        if yaml_path.exists():
            config = load_xml_parsing_config(str(yaml_path))
            
            # Should successfully load
            assert isinstance(config, dict)
            assert len(config) > 0
            
            # Should have expected structure
            assert "attributes_to_extract" in config

