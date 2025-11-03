import json
import os
from copy import deepcopy
from itertools import cycle, islice
from random import randint

import trio
from sys import stderr
from trio_websocket import open_websocket_url

URL_FOR_BUSSES_UPDATE = 'ws://localhost:8080'


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path)[:200]:
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


async def run_bus(url, bus_id, route):
    bus = {
        "busId": bus_id,
        "route": route['name'],
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
            quantity_of_points = len(route['coordinates'])
            route['coordinates'] = cycle(route['coordinates'])
            quantity_uf_buses = randint(1, 3)


            for bus_index in range(quantity_uf_buses):
                route_copy = deepcopy(route)
                route_copy['coordinates'] = islice(route_copy['coordinates'], int(quantity_of_points / (bus_index + 1)), None)

                bus_id = generate_bus_id(route_copy['name'], bus_index)

                nursery.start_soon(run_bus, URL_FOR_BUSSES_UPDATE, bus_id, route_copy)


trio.run(run_busses)
