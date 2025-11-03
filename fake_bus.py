import json
import os

import trio
from sys import stderr
from trio_websocket import open_websocket_url

URL_FOR_BUSSES_UPDATE = 'ws://localhost:8080' # for face buses


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


async def run_bus(url, bus_id, route):
    bus = {
        "busId": bus_id,
        "route": bus_id
    }
    while True:
        for coord in route['coordinates']:
            lat = coord[0]
            lng = coord[1]
            bus["lat"] = lat
            bus["lng"] = lng

            json_data = json.dumps(bus, ensure_ascii=False)

            try:
                async with open_websocket_url(url) as ws:
                    await ws.send_message(json_data)
                    await trio.sleep(2)
            except OSError as ose:
                print('Connection attempt failed: %s' % ose, file=stderr)


async def run_busses():
    async with trio.open_nursery() as nursery:
        for route in load_routes():
            bus_id = route['name']
            nursery.start_soon(run_bus, URL_FOR_BUSSES_UPDATE, bus_id, route)


trio.run(run_busses)
