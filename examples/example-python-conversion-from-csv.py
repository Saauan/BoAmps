#!/usr/bin/env python3
"""
Input:  ./rse_export.csv
Output: ./reports/{run_id}.json (one file per CSV row)
"""

import pandas as pd
import json
import os
from datetime import datetime
from typing import Dict, Any

NUMBER_OF_INFERENCES_PER_EVALUATION = 709

class BoAmpsReportGenerator:
    """Generator for BoAmps-compliant JSON reports from CSV data."""
    
    def __init__(self, csv_path: str = "./rse_export.csv", output_dir: str = "./reports"):
        """
        Initialize the report generator.
        
        Args:
            csv_path: Path to the input CSV file
            output_dir: Directory where JSON reports will be saved
        """
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.format_version = "1.0.0"
        self.format_uri = "https://raw.githubusercontent.com/Boavizta/BoAmps/main/model/report_schema.json"
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def load_csv_data(self) -> pd.DataFrame:
        """Load and return the CSV data as a pandas DataFrame."""
        try:
            df = pd.read_csv(filepath_or_buffer=self.csv_path, sep=',')
            print(f"✓ Loaded {len(df)} rows from {self.csv_path}")
            return df
        except FileNotFoundError:
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
        except Exception as e:
            raise Exception(f"Error loading CSV: {str(e)}")
    
    def create_header_section(self, run_id: str) -> Dict[str, Any]:
        """Create the header section of the BoAmps report."""
        return {
            "licensing": "open-data",
            "formatVersion": self.format_version,
            "formatVersionSpecificationUri": self.format_uri,
            "reportId": str(run_id),
            "reportDatetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reportStatus": "draft",
            "publisher": {
                "name": "My Company",
                "division": "Innov",
                "projectName": "LLM Bench",
                "confidentialityLevel": "public"
            }
        }
    
    def create_task_section(self, row: pd.Series) -> Dict[str, Any]:
        """Create the task section based on CSV row data."""
        # Extract model information
        model_name = str(row.get('model_name', 'unknown'))
        model_url = str(row.get('model_url', '')) if pd.notna(row.get('model_url')) else None
        
        # Determine if this is a commercial API or open model
        is_commercial_api = model_name.lower() in ['gpt-4o-mini', 'gemini-2.5-pro-low']
        
        # Create algorithm section
        algorithm = {
            "algorithmType": "llm",
            "algorithmName": "transformer",
        }
        
        if not is_commercial_api and model_url:
            algorithm["foundationModelName"] = model_name
            algorithm["foundationModelUri"] = model_url
        else:
            algorithm["foundationModelName"] = model_name
        
        # Add parameters number (model size in billions)
        model_size = float(row.get('model_size', 0)) if pd.notna(row.get('model_size')) else None
        if model_size:
            algorithm["parametersNumber"] = model_size
        
        # Create dataset sections (input and output)
        input_tokens = int(row.get('input_tokens', 0)) if pd.notna(row.get('input_tokens')) else 0
        output_tokens = int(row.get('output_tokens', 0)) if pd.notna(row.get('output_tokens')) else 0
        
        datasets = [
            {
                "dataUsage": "input",
                "dataType": "token",
                "datasetName": "inference_input",
                "dataQuantity": input_tokens,
                "datasetDescription": "Total input tokens"
            },
            {
                "dataUsage": "output",
                "dataType": "token", 
                "datasetName": "inference_output",
                "dataQuantity": output_tokens,
                "datasetDescription": "Total output tokens"
            }
        ]
        
        task_section = {
            "taskStage": "inference",
            "taskFamily": "text generation",
            "nbRequest": NUMBER_OF_INFERENCES_PER_EVALUATION,
            "algorithms": [algorithm],
            "dataset": datasets,
            "taskDescription": f"LLM inference using {model_name}"
        }
        
        # Add accuracy if available
        instruct_score = row.get('instruct_score')
        if pd.notna(instruct_score):
            task_section["measuredAccuracy"] = float(instruct_score) / 5.0  # Normalize to 0-1 if scored on 1-5
        
        return task_section
    
    def create_measures_section(self, row: pd.Series) -> list:
        """Create the measures section based on CSV row data."""
        duration = float(row.get('total_duration', 0)) if pd.notna(row.get('total_duration')) else None
        energy = row.get('total energy')  # Note: space in column name
        energy_kwh = float(energy) 
        
        measure = {
            "measurementMethod": "codecarbon",
            "version": "2.x",
        }
        
        if duration:
            measure["duration"] = duration  # in seconds
        
        if energy_kwh:
            measure["powerConsumption"] = energy_kwh  # in kWh
        
        # Add GPU information if available
        gpu_model = row.get('gpu_model')
        if pd.notna(gpu_model) and gpu_model:
            measure["gpuTrackingMode"] = "hardware_monitoring"
        
        # Add CPU tracking mode
        measure["cpuTrackingMode"] = "constant"
        
        return [measure]
    
    def create_system_section(self) -> Dict[str, Any]:
        """Create the system section with default values."""
        return {
            "os": "linux"
        }
    
    def create_software_section(self) -> Dict[str, Any]:
        """Create the software section with default values."""
        return {
            "language": "python",
            "version": "3.x"
        }
    
    def create_infrastructure_section(self, row: pd.Series) -> Dict[str, Any]:
        """Create the infrastructure section based on CSV row data."""
        node_name = None
        gpu_model = str(row.get('gpu_model', '')) if pd.notna(row.get('gpu_model')) else None
        gpu_mem = str(row.get('gpu_mem', '')) if pd.notna(row.get('gpu_mem')) else None
        num_gpu = int(row.get('num_gpu', 0)) if pd.notna(row.get('num_gpu')) else None
        
        infrastructure = {
            "infraType": "onPremise"
        }
        
        # Add hardware components if available
        components = []
        
        # Add GPU information
        if num_gpu and num_gpu > 0:
            gpu_name = "unknown" if not gpu_model or gpu_model == '' else gpu_model.replace('gpu_', '').upper()
            gpu_component = {
                "componentName": gpu_name,
                "componentType": "gpu", 
                "nbComponent": int(num_gpu),
                "manufacturer": "nvidia" if gpu_model and "gpu" in gpu_model.lower() else "unknown"
            }
            if gpu_mem:
                mem_size = gpu_mem.replace('gpu_mem_', '')
                gpu_component["memorySize"] = int(mem_size) if mem_size.isdigit() else None
            components.append(gpu_component)
                        
        # If no GPU components were added (e.g., commercial APIs), add a generic compute component
        if not any(comp["componentType"] == "gpu" for comp in components):
            components.append({
                "componentName": "unknown",
                "componentType": "gpu",
                "nbComponent": 1,
                "componentDescription": "default unknown GPU model"
            })
                
        infrastructure["components"] = components
        
        if node_name:
            infrastructure["nodeIdentifier"] = node_name
            
        return infrastructure
    
    def create_report(self, row: pd.Series) -> Dict[str, Any]:
        """Create a complete BoAmps report from a CSV row."""
        run_id = str(row['run_id'])
        
        report = {
            "header": self.create_header_section(run_id),
            "task": self.create_task_section(row),
            "measures": self.create_measures_section(row),
            "system": self.create_system_section(),
            "software": self.create_software_section(),
            "infrastructure": self.create_infrastructure_section(row)
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str) -> None:
        """Save a report to a JSON file."""
        filepath = os.path.join(self.output_dir, f"{filename}.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved report: {filepath}")
        except Exception as e:
            print(f"✗ Error saving report {filename}: {str(e)}")
    
    def generate_reports(self) -> None:
        """Main method to generate all reports from CSV data."""
        print("🚀 Starting BoAmps report generation...")
        
        # Load CSV data
        df = self.load_csv_data()
        
        # Generate report for each row
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                run_id = str(row['run_id'])
                report = self.create_report(row)
                self.save_report(report, f"report_bench_llm_{run_id}")
                success_count += 1
            except Exception as e:
                print(f"✗ Error processing row {index}: {str(e)}")
                error_count += 1
        
        print(f"\n📊 Generation completed:")
        print(f"   ✓ Successfully generated: {success_count} reports")
        print(f"   ✗ Errors: {error_count}")
        print(f"   📁 Reports saved in: {self.output_dir}")
        
        if success_count > 0:
            print(f"\n💡 Next steps:")
            print(f"   - Validate reports using: python ../tools/schema_validator/validate-schema.py")
            print(f"   - Review and customize the generated reports as needed")
            print(f"   - TODO: Column handling can be refined in the create_*_section methods")


def main():
    """Main entry point."""
    try:
        generator = BoAmpsReportGenerator()
        generator.generate_reports()
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
