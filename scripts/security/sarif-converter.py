#!/usr/bin/env python3
"""
SARIF Converter for Security Scanning Tools
Converts tfsec, checkov, and terrascan output to SARIF format for GitHub Code Scanning
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class SARIFConverter:
    """Converts security tool outputs to SARIF format"""
    
    def __init__(self):
        self.sarif_template = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": []
        }
    
    def create_tool_driver(self, tool_name: str, version: str = "1.0.0") -> Dict[str, Any]:
        """Create SARIF tool driver section"""
        drivers = {
            "tfsec": {
                "name": "tfsec",
                "version": version,
                "informationUri": "https://github.com/aquasecurity/tfsec",
                "shortDescription": {"text": "Security scanner for Terraform"},
                "fullDescription": {"text": "tfsec uses static analysis of your terraform code to spot potential misconfigurations."}
            },
            "checkov": {
                "name": "Checkov",
                "version": version,
                "informationUri": "https://github.com/bridgecrewio/checkov",
                "shortDescription": {"text": "Static code analysis tool for infrastructure as code"},
                "fullDescription": {"text": "Checkov is a static code analysis tool for infrastructure as code (IaC) and also a software composition analysis (SCA) tool for images and open source packages."}
            },
            "terrascan": {
                "name": "Terrascan",
                "version": version,
                "informationUri": "https://github.com/tenable/terrascan",
                "shortDescription": {"text": "Detect compliance and security violations across Infrastructure as Code"},
                "fullDescription": {"text": "Terrascan is a static code analyzer for Infrastructure as Code to mitigate risk before provisioning cloud native infrastructure."}
            }
        }
        
        return drivers.get(tool_name, {
            "name": tool_name,
            "version": version,
            "informationUri": f"https://github.com/{tool_name}",
            "shortDescription": {"text": f"Security scanner: {tool_name}"}
        })
    
    def severity_to_level(self, severity: str) -> str:
        """Convert tool severity to SARIF level"""
        severity_map = {
            "CRITICAL": "error",
            "HIGH": "error", 
            "MEDIUM": "warning",
            "LOW": "note",
            "INFO": "note",
            "WARNING": "warning",
            "ERROR": "error"
        }
        return severity_map.get(severity.upper(), "warning")
    
    def convert_tfsec_to_sarif(self, tfsec_results: Dict[str, Any]) -> Dict[str, Any]:
        """Convert tfsec JSON output to SARIF format"""
        
        tool_driver = self.create_tool_driver("tfsec")
        results = []
        rules = {}
        
        if "results" in tfsec_results:
            for issue in tfsec_results["results"]:
                rule_id = issue.get("rule_id", "unknown-rule")
                
                # Create rule definition
                if rule_id not in rules:
                    rules[rule_id] = {
                        "id": rule_id,
                        "name": rule_id,
                        "shortDescription": {"text": issue.get("description", "Unknown issue")},
                        "fullDescription": {"text": issue.get("long_description", issue.get("description", "Unknown issue"))},
                        "help": {
                            "text": issue.get("resolution", "Review and fix the security issue"),
                            "markdown": f"**Resolution**: {issue.get('resolution', 'Review and fix the security issue')}\n\n**Links**: {', '.join(issue.get('links', []))}"
                        },
                        "properties": {
                            "severity": issue.get("severity", "UNKNOWN"),
                            "category": "security"
                        }
                    }
                
                # Create result
                result = {
                    "ruleId": rule_id,
                    "level": self.severity_to_level(issue.get("severity", "WARNING")),
                    "message": {"text": issue.get("description", "Security issue detected")},
                    "locations": []
                }
                
                # Add location information
                if "location" in issue:
                    location = issue["location"]
                    result["locations"].append({
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": location.get("filename", "unknown"),
                                "uriBaseId": "%SRCROOT%"
                            },
                            "region": {
                                "startLine": location.get("start_line", 1),
                                "endLine": location.get("end_line", 1),
                                "startColumn": 1,
                                "endColumn": 80
                            }
                        }
                    })
                
                results.append(result)
        
        # Create SARIF run
        run = {
            "tool": {
                "driver": {
                    **tool_driver,
                    "rules": list(rules.values())
                }
            },
            "results": results,
            "columnKind": "utf16CodeUnits"
        }
        
        sarif_output = self.sarif_template.copy()
        sarif_output["runs"] = [run]
        
        return sarif_output
    
    def convert_checkov_to_sarif(self, checkov_results: Dict[str, Any]) -> Dict[str, Any]:
        """Convert checkov JSON output to SARIF format"""
        
        tool_driver = self.create_tool_driver("checkov")
        results = []
        rules = {}
        
        if "results" in checkov_results and "failed_checks" in checkov_results["results"]:
            for check in checkov_results["results"]["failed_checks"]:
                rule_id = check.get("check_id", "unknown-check")
                
                # Create rule definition
                if rule_id not in rules:
                    rules[rule_id] = {
                        "id": rule_id,
                        "name": check.get("check_name", rule_id),
                        "shortDescription": {"text": check.get("check_name", "Unknown check")},
                        "fullDescription": {"text": check.get("description", check.get("check_name", "Unknown check"))},
                        "help": {
                            "text": check.get("guideline", "Review and fix the security issue"),
                            "markdown": f"**Guideline**: {check.get('guideline', 'Review and fix the security issue')}"
                        },
                        "properties": {
                            "severity": check.get("severity", "UNKNOWN"),
                            "category": "security"
                        }
                    }
                
                # Create result
                result = {
                    "ruleId": rule_id,
                    "level": self.severity_to_level(check.get("severity", "WARNING")),
                    "message": {"text": check.get("check_name", "Security check failed")},
                    "locations": []
                }
                
                # Add location information
                if "file_path" in check:
                    location_info = {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": check["file_path"],
                                "uriBaseId": "%SRCROOT%"
                            },
                            "region": {
                                "startLine": check.get("file_line_range", [1])[0],
                                "endLine": check.get("file_line_range", [1])[-1] if check.get("file_line_range") else 1,
                                "startColumn": 1,
                                "endColumn": 80
                            }
                        }
                    }
                    result["locations"].append(location_info)
                
                results.append(result)
        
        # Create SARIF run
        run = {
            "tool": {
                "driver": {
                    **tool_driver,
                    "rules": list(rules.values())
                }
            },
            "results": results,
            "columnKind": "utf16CodeUnits"
        }
        
        sarif_output = self.sarif_template.copy()
        sarif_output["runs"] = [run]
        
        return sarif_output
    
    def convert_terrascan_to_sarif(self, terrascan_results: Dict[str, Any]) -> Dict[str, Any]:
        """Convert terrascan JSON output to SARIF format"""
        
        tool_driver = self.create_tool_driver("terrascan")
        results = []
        rules = {}
        
        if "results" in terrascan_results and "violations" in terrascan_results["results"]:
            for violation in terrascan_results["results"]["violations"]:
                rule_id = violation.get("rule_id", violation.get("rule_name", "unknown-rule"))
                
                # Create rule definition
                if rule_id not in rules:
                    rules[rule_id] = {
                        "id": rule_id,
                        "name": violation.get("rule_name", rule_id),
                        "shortDescription": {"text": violation.get("description", "Security violation")},
                        "fullDescription": {"text": violation.get("description", "Security violation detected")},
                        "help": {
                            "text": "Review and fix the security violation",
                            "markdown": f"**Category**: {violation.get('category', 'Unknown')}\n**Resource**: {violation.get('resource_type', 'Unknown')}"
                        },
                        "properties": {
                            "severity": violation.get("severity", "UNKNOWN"),
                            "category": "security"
                        }
                    }
                
                # Create result
                result = {
                    "ruleId": rule_id,
                    "level": self.severity_to_level(violation.get("severity", "MEDIUM")),
                    "message": {"text": violation.get("description", "Security violation detected")},
                    "locations": []
                }
                
                # Add location information
                if "file" in violation:
                    result["locations"].append({
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": violation["file"],
                                "uriBaseId": "%SRCROOT%"
                            },
                            "region": {
                                "startLine": violation.get("line", 1),
                                "endLine": violation.get("line", 1),
                                "startColumn": 1,
                                "endColumn": 80
                            }
                        }
                    })
                
                results.append(result)
        
        # Create SARIF run
        run = {
            "tool": {
                "driver": {
                    **tool_driver,
                    "rules": list(rules.values())
                }
            },
            "results": results,
            "columnKind": "utf16CodeUnits"
        }
        
        sarif_output = self.sarif_template.copy()
        sarif_output["runs"] = [run]
        
        return sarif_output
    
    def merge_sarif_files(self, sarif_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple SARIF files into one"""
        
        merged_sarif = self.sarif_template.copy()
        merged_runs = []
        
        for sarif_data in sarif_files:
            if "runs" in sarif_data:
                merged_runs.extend(sarif_data["runs"])
        
        merged_sarif["runs"] = merged_runs
        return merged_sarif


def main():
    """Main function to handle command line conversion"""
    
    if len(sys.argv) < 4:
        print("Usage: python sarif-converter.py <tool> <input_file> <output_file>")
        print("Tools: tfsec, checkov, terrascan, merge")
        sys.exit(1)
    
    tool = sys.argv[1]
    input_file = sys.argv[2] 
    output_file = sys.argv[3]
    
    converter = SARIFConverter()
    
    try:
        if tool == "merge":
            # Merge multiple SARIF files
            sarif_files = []
            for sarif_path in Path(input_file).glob("*.sarif"):
                with open(sarif_path, 'r') as f:
                    sarif_files.append(json.load(f))
            
            merged_sarif = converter.merge_sarif_files(sarif_files)
            
            with open(output_file, 'w') as f:
                json.dump(merged_sarif, f, indent=2)
            
            print(f"✅ Merged {len(sarif_files)} SARIF files to {output_file}")
            
        else:
            # Convert tool output to SARIF
            with open(input_file, 'r') as f:
                tool_results = json.load(f)
            
            if tool == "tfsec":
                sarif_output = converter.convert_tfsec_to_sarif(tool_results)
            elif tool == "checkov":
                sarif_output = converter.convert_checkov_to_sarif(tool_results)
            elif tool == "terrascan":
                sarif_output = converter.convert_terrascan_to_sarif(tool_results)
            else:
                print(f"❌ Unknown tool: {tool}")
                sys.exit(1)
            
            with open(output_file, 'w') as f:
                json.dump(sarif_output, f, indent=2)
            
            print(f"✅ Converted {tool} results to SARIF: {output_file}")
    
    except Exception as e:
        print(f"❌ Error converting {tool} results: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()