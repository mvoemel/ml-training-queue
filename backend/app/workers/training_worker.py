"""
This worker is started by the scheduler service.
The actual job processing happens in the scheduler itself.
This file exists to support the docker-compose setup.
"""
import asyncio
from ..services.job_scheduler import JobScheduler

async def main():
    scheduler = JobScheduler()
    await scheduler.run()

if __name__ == "__main__":
    asyncio.run(main())