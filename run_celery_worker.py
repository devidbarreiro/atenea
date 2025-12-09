#!/usr/bin/env python
"""
Cross-platform Celery worker runner
Automatically uses correct pool based on OS
"""
import os
import sys
import platform
import subprocess

def run_celery_worker():
    """Run Celery worker with OS-appropriate settings"""
    
    queues = [
        'video_generation',
        'image_generation',
        'audio_generation',
        'scene_processing',
        'default',
        'polling_tasks',
        'maintenance'
    ]
    
    queue_arg = ','.join(queues)
    
    # Base command
    cmd = [
        'celery',
        '-A', 'atenea',
        'worker',
        '--loglevel=info',
        f'--queues={queue_arg}',
        '--concurrency=4',
    ]
    
    # Add pool-specific settings based on OS
    os_name = platform.system()
    if os_name == 'Windows':
        cmd.append('--pool=threads')
        print("🪟 Running on Windows: using thread pool")
    else:
        cmd.append('--pool=prefork')
        print(f"🐧 Running on {os_name}: using prefork (multiprocessing)")
    
    print(f"Starting Celery worker with: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\nCelery worker stopped.")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"\nCelery worker exited with error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_celery_worker()
