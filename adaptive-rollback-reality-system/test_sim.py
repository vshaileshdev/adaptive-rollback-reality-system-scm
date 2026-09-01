
import asyncio
from backend.simulation import simulation_engine
from backend.dataset_loader import dataset_loader

async def main():
    simulation_engine.start()
    for _ in range(5):
        await asyncio.sleep(0.5)
        print('Current index:', dataset_loader.current_idx)
    simulation_engine.stop()

asyncio.run(main())

