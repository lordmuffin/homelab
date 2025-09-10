#!/usr/bin/env python3
"""
Test suite for seed inventory parser.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from seed.seed_parser import SeedParser, SeedInventory
from seed.validator import SeedValidator


class TestSeedParser:
    """Test cases for SeedParser class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.parser = SeedParser()
    
    def test_parse_valid_seed_file(self):
        """Test parsing a valid seed inventory file."""
        seed_data = {
            'version': '1.0',
            'name': 'Test Infrastructure',
            'networks': [
                {
                    'network': '192.168.1.0/24',
                    'name': 'Test Network'
                }
            ],
            'known_hosts': [
                {
                    'ip': '192.168.1.10',
                    'hostname': 'test-host'
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(seed_data, f)
            temp_file = Path(f.name)
        
        try:
            result = self.parser.parse_seed_file(temp_file)
            
            assert result['version'] == '1.0'
            assert result['name'] == 'Test Infrastructure'
            assert len(result['networks']) == 1
            assert len(result['known_hosts']) == 1
            assert result['networks'][0]['network'] == '192.168.1.0/24'
            assert result['known_hosts'][0]['ip'] == '192.168.1.10'
            
        finally:
            temp_file.unlink()
    
    def test_parse_invalid_network(self):
        """Test parsing with invalid network CIDR."""
        seed_data = {
            'version': '1.0',
            'networks': [
                {
                    'network': 'invalid-network',
                    'name': 'Invalid Network'
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(seed_data, f)
            temp_file = Path(f.name)
        
        try:
            with pytest.raises(Exception):
                self.parser.parse_seed_file(temp_file)
        finally:
            temp_file.unlink()
    
    def test_parse_invalid_ip(self):
        """Test parsing with invalid IP address."""
        seed_data = {
            'version': '1.0',
            'known_hosts': [
                {
                    'ip': 'invalid-ip',
                    'hostname': 'test-host'
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(seed_data, f)
            temp_file = Path(f.name)
        
        try:
            with pytest.raises(Exception):
                self.parser.parse_seed_file(temp_file)
        finally:
            temp_file.unlink()
    
    def test_create_sample_seed_file(self):
        """Test creating sample seed file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "sample_seed.yml"
            
            created_file = self.parser.create_sample_seed_file(output_file)
            
            assert created_file.exists()
            
            # Verify sample file is valid
            result = self.parser.parse_seed_file(created_file)
            assert 'networks' in result
            assert 'known_hosts' in result
            assert len(result['networks']) > 0
            assert len(result['known_hosts']) > 0
    
    def test_get_networks_for_discovery(self):
        """Test extracting networks sorted by priority."""
        seed_data = {
            'networks': [
                {
                    'network': '10.0.0.0/24',
                    'name': 'Network 2',
                    'discovery_priority': 2
                },
                {
                    'network': '192.168.1.0/24', 
                    'name': 'Network 1',
                    'discovery_priority': 1
                }
            ]
        }
        
        networks = self.parser.get_networks_for_discovery(seed_data)
        
        assert len(networks) == 2
        # Should be sorted by priority (lower number = higher priority)
        assert networks[0]['network'] == '192.168.1.0/24'
        assert networks[1]['network'] == '10.0.0.0/24'
    
    def test_merge_seed_files(self):
        """Test merging multiple seed files."""
        seed1_data = {
            'version': '1.0',
            'networks': [
                {'network': '192.168.1.0/24', 'name': 'Network 1'}
            ],
            'known_hosts': [
                {'ip': '192.168.1.10', 'hostname': 'host1'}
            ]
        }
        
        seed2_data = {
            'version': '1.0', 
            'networks': [
                {'network': '10.0.0.0/24', 'name': 'Network 2'}
            ],
            'known_hosts': [
                {'ip': '10.0.0.10', 'hostname': 'host2'}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f1:
            yaml.dump(seed1_data, f1)
            temp_file1 = Path(f1.name)
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f2:
            yaml.dump(seed2_data, f2)
            temp_file2 = Path(f2.name)
        
        try:
            merged = self.parser.merge_seed_files([temp_file1, temp_file2])
            
            assert len(merged['networks']) == 2
            assert len(merged['known_hosts']) == 2
            
            # Check networks
            network_cidrs = [net['network'] for net in merged['networks']]
            assert '192.168.1.0/24' in network_cidrs
            assert '10.0.0.0/24' in network_cidrs
            
            # Check hosts
            host_ips = [host['ip'] for host in merged['known_hosts']]
            assert '192.168.1.10' in host_ips
            assert '10.0.0.10' in host_ips
            
        finally:
            temp_file1.unlink()
            temp_file2.unlink()


class TestSeedValidator:
    """Test cases for SeedValidator class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.validator = SeedValidator()
    
    def test_validate_network_overlaps(self):
        """Test network overlap detection."""
        seed_data = {
            'networks': [
                {'network': '192.168.1.0/24', 'name': 'Network 1'},
                {'network': '192.168.1.0/25', 'name': 'Network 2'}  # Overlaps
            ]
        }
        
        warnings = self.validator.validate_network_overlaps(seed_data)
        
        assert len(warnings) > 0
        assert 'overlap' in warnings[0].lower()
    
    def test_validate_known_host_consistency(self):
        """Test known host consistency validation."""
        seed_data = {
            'known_hosts': [
                {'ip': '192.168.1.10', 'hostname': 'host1'},
                {'ip': '192.168.1.10', 'hostname': 'host2'}  # Duplicate IP
            ]
        }
        
        warnings = self.validator.validate_known_host_consistency(seed_data)
        
        assert len(warnings) > 0
        assert 'duplicate' in warnings[0].lower()
    
    def test_validate_network_host_consistency(self):
        """Test network-host consistency validation."""
        seed_data = {
            'networks': [
                {'network': '192.168.1.0/24', 'name': 'Network 1'}
            ],
            'known_hosts': [
                {'ip': '10.0.0.10', 'hostname': 'host1'}  # Not in network
            ]
        }
        
        warnings = self.validator.validate_network_host_consistency(seed_data)
        
        assert len(warnings) > 0
        assert 'not within' in warnings[0].lower()
    
    def test_comprehensive_validation_success(self):
        """Test comprehensive validation with valid data."""
        seed_data = {
            'version': '1.0',
            'networks': [
                {'network': '192.168.1.0/24', 'name': 'Network 1'}
            ],
            'known_hosts': [
                {'ip': '192.168.1.10', 'hostname': 'host1'}
            ]
        }
        
        is_valid, errors, warnings = self.validator.comprehensive_validation(seed_data)
        
        assert is_valid == True
        assert len(errors) == 0
    
    def test_comprehensive_validation_failure(self):
        """Test comprehensive validation with invalid data."""
        seed_data = {
            'version': '1.0',
            # Missing networks and known_hosts (should fail)
        }
        
        is_valid, errors, warnings = self.validator.comprehensive_validation(seed_data)
        
        assert is_valid == False
        assert len(errors) > 0
    
    def test_suggest_fixes(self):
        """Test fix suggestions generation."""
        seed_data = {
            'version': '1.0',
            'networks': [
                {'network': '192.168.1.0/24', 'name': 'Network 1'}
            ]
            # Missing known hosts - should suggest adding them
        }
        
        suggestions = self.validator.suggest_fixes(seed_data)
        
        assert len(suggestions) > 0
        # Should suggest adding known hosts
        assert any('known' in suggestion.lower() for suggestion in suggestions)


if __name__ == '__main__':
    pytest.main([__file__])