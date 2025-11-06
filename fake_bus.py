import json
import logging
import os
from copy import deepcopy
from functools import wraps
from itertools import cycle, islice
from random import randint, choice

import trio
import trio_websocket
from trio_websocket import open_websocket_url
import asyncclick as click


def load_routes(quantity_of_routes, directory_path='routes'):
    if quantity_of_routes is None:
        filesname = os.listdir(directory_path)
    else:
        filesname = os.listdir(directory_path)[:quantity_of_routes]

    for filename in filesname:
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


def relaunch_on_disconnect(async_function):
    @wraps(async_function)
    async def wrapper(*args, **kwargs):
        while True:
            try:
                result = await async_function(*args, **kwargs)
                return result
            except trio_websocket.ConnectionClosed as error:
                logging.error('Lost connection to server')
                await trio.sleep(5)
                continue

    return wrapper


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


@relaunch_on_disconnect
async def send_updates(server_address, receive_channel, refresh_timeout):
    try:
        async with open_websocket_url(server_address) as ws:
            while True:
                async for message in receive_channel:
                    await ws.send_message(message)
                    await trio.sleep(refresh_timeout)
    except OSError as ose:
        logging.error('Connection attempt failed: %s' % ose)


@click.command()
@click.option('-s', '--server', type=str, default='ws://localhost:8080', required=False, help="Server address.")
@click.option('-r', '--routes_number', type=int, default=None, required=False, help="Quantity of routes")
@click.option('-b', '--buses_per_route', type=int, default=1, required=False, help="Quantity of busses on one route.")
@click.option('-ws', '--websockets_number', type=int, default=10, required=False, help="Quantity of websockets")
@click.option('-id', '--emulator_id', type=str, default=None, required=False, help="prefix to BusID.")
@click.option('-t', '--refresh_timeout', type=float, default=1, required=False,
              help="Delay in updating server coordinates.")
@click.option('-v', '--v', type=bool, default=False, required=False, help="Turn on logging")
async def run_busses(server, routes_number, buses_per_route, websockets_number, emulator_id, refresh_timeout, v):
    if v:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.disable(logging.CRITICAL)

    async with trio.open_nursery() as nursery:

        channels = []
        for channel in range(websockets_number):
            send_channel, receive_channel = trio.open_memory_channel(100)

            nursery.start_soon(send_updates, server, receive_channel, refresh_timeout)

            channels.append([send_channel, receive_channel])

        for route in load_routes(quantity_of_routes=routes_number):
            quantity_of_points = len(route['coordinates'])
            route['coordinates'] = cycle(route['coordinates'])
            quantity_uf_buses = randint(1, buses_per_route)

            for bus_index in range(quantity_uf_buses):
                channel = choice(channels)
                route_copy = deepcopy(route)
                route_copy['coordinates'] = islice(route_copy['coordinates'], int(quantity_of_points / (bus_index + 1)),
                                                   None)

                bus_id = generate_bus_id(route_copy['name'], bus_index)
                if emulator_id is not None:
                    bus_id = f'{emulator_id}-{bus_id}'

                nursery.start_soon(run_bus, channel[0], bus_id, route_copy)


if __name__ == '__main__':
    trio.run(run_busses.main)
