"""Long-running collector process."""
import asyncio
import os
import signal
from collector import AdaptiveScheduler, LightweightCollector
from pusher import PushEngine


async def run() -> None:
    endpoint = os.getenv("OC_MONITOR_ENDPOINT", "http://127.0.0.1:8000")
    token = os.getenv("INGEST_TOKEN") or os.getenv("OC_MONITOR_TOKEN", "")
    gateway_port = int(os.getenv("OPENCLAW_GATEWAY_PORT", "18789"))
    batch_size = int(os.getenv("OC_MONITOR_BATCH_SIZE", "10"))
    batch_window = int(os.getenv("OC_MONITOR_BATCH_WINDOW", "5"))

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    collector = LightweightCollector(gateway_port=gateway_port)
    scheduler = AdaptiveScheduler(collector)
    pusher = PushEngine(endpoint=endpoint, token=token, batch_size=batch_size, batch_window=batch_window)

    async def collect_once():
        snapshot = await collector.collect()
        await pusher.push(snapshot)
        scheduler._adjust_interval(snapshot)

    try:
        while not stop_event.is_set():
            await collect_once()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=scheduler.get_interval())
            except asyncio.TimeoutError:
                pass
    finally:
        await pusher.flush_cached_data()
        await pusher.close()


if __name__ == "__main__":
    asyncio.run(run())
