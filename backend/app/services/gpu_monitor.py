import subprocess
import re
from typing import List, Optional
from ..logger import Logger

class GPUMonitor:
    def get_available_gpus(self) -> List[dict]:
        """Get list of available GPUs using nvidia-smi"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=index,name,memory.total', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                check=True
            )
            
            gpus = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(', ')
                    gpus.append({
                        'id': int(parts[0]),
                        'name': parts[1],
                        'memory': int(parts[2])
                    })
            
            return gpus
        except Exception as e:
            Logger.error(f"Error getting GPUs: {e}")
            
            return []
    
    def get_gpu_stats(self, gpu_id: int) -> Optional[dict]:
        """Get current GPU statistics"""
        try:
            result = subprocess.run(
                [
                    'nvidia-smi',
                    '--query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu',
                    '--format=csv,noheader,nounits',
                    f'--id={gpu_id}'
                ],
                capture_output=True,
                text=True,
                check=True
            )
            
            line = result.stdout.strip()
            if line:
                parts = line.split(', ')
                return {
                    'gpu_id': int(parts[0]),
                    'utilization': float(parts[1]),
                    'memory_used': int(parts[2]),
                    'memory_total': int(parts[3]),
                    'temperature': float(parts[4])
                }
            
            return None
        except Exception as e:
            Logger.error(f"Error getting GPU stats: {e}")
            return None