import json
import os
from copy import deepcopy
from itertools import cycle, islice
from random import randint, choice

import trio
from sys import stderr
from trio_websocket import open_websocket_url

URL_FOR_BUSSES_UPDATE = 'ws://localhost:8080'
QUANTITY_UF_CHANNELS = 10
DUPLICATE_BUSES = 70


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


async def run_bus(send_channel, bus_id, route):
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
            await send_channel.send(json_data)
            await trio.sleep(1)


async def send_updates(server_address, receive_channel):
    try:
        async with open_websocket_url(server_address) as ws:
            while True:
                async for message in receive_channel:
                    await ws.send_message(message)
                    await trio.sleep(0.1)
    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)


async def run_busses():
    async with trio.open_nursery() as nursery:

        channels = []
        for channel in range(QUANTITY_UF_CHANNELS):
            send_channel, receive_channel = trio.open_memory_channel(100)

            nursery.start_soon(send_updates, URL_FOR_BUSSES_UPDATE, receive_channel)

            channels.append([send_channel, receive_channel])

        for route in load_routes():
            quantity_of_points = len(route['coordinates'])
            route['coordinates'] = cycle(route['coordinates'])
            quantity_uf_buses = randint(1, DUPLICATE_BUSES)

            for bus_index in range(quantity_uf_buses):
                channel = choice(channels)
                route_copy = deepcopy(route)
                route_copy['coordinates'] = islice(route_copy['coordinates'], int(quantity_of_points / (bus_index + 1)),
                                                   None)

                bus_id = generate_bus_id(route_copy['name'], bus_index)

                nursery.start_soon(run_bus, channel[0], bus_id, route_copy)


trio.run(run_busses)
