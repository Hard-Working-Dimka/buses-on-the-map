import json
import logging
from contextlib import suppress
from dataclasses import dataclass, asdict
from functools import partial

import trio
import trio_websocket
from trio_websocket import serve_websocket, ConnectionClosed
import asyncclick as click

from data_validators import validate_bus_response, validate_browser_response

BUSES = {}


@dataclass
class Bus:
    busId: str
    lat: float
    lng: float
    route: str

    def update(self, lat, lng):
        self.lat = lat
        self.lng = lng


@dataclass
class WindowBounds:
    south_lat: float = 0.0
    north_lat: float = 0.0
    west_lng: float = 0.0
    east_lng: float = 0.0

    def is_inside(self, lat, lng):
        s_lat = self.south_lat
        n_lng = self.north_lat
        w_lng = self.west_lng
        e_lng = self.east_lng
        return (s_lat <= lat) and (lat <= n_lng) and (w_lng <= lng) and (lng <= e_lng)

    def update(self, south_lat, north_lat, west_lng, east_lng):
        self.south_lat = south_lat
        self.north_lat = north_lat
        self.west_lng = west_lng
        self.east_lng = east_lng


async def listen_browser(ws, bounds: WindowBounds):
    while True:
        try:
            response = await ws.get_message()
            logging.debug(response)

            result_of_validation = validate_browser_response(response)
            if not result_of_validation['valid']:
                await ws.send_message(json.dumps(result_of_validation['errors']))
                continue
            bounds_new = json.loads(response)
            bounds_new = bounds_new['data']
            bounds.update(**bounds_new)
            await trio.sleep(5)
        except trio_websocket.ConnectionClosed:
            break


async def send_new_location(ws, bounds: WindowBounds):
    bounds = bounds
    while True:
        try:
            buses_location = {
                "msgType": "Buses",
                "buses": []
            }

            for bus in BUSES.values():
                if bounds.is_inside(bus.lat, bus.lng):
                    buses_location['buses'].append(asdict(bus))

            buses_location = json.dumps(buses_location)
            await ws.send_message(buses_location)
            await trio.sleep(0.1)
        except ConnectionClosed:
            break


async def talk_to_browser(request):
    bounds = WindowBounds()
    ws = await request.accept()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(listen_browser, ws, bounds)
        nursery.start_soon(send_new_location, ws, bounds)


async def update_current_location(request):
    ws = await request.accept()
    while True:
        try:
            current_location = await ws.get_message()

            result_of_validation = validate_bus_response(current_location)
            if not result_of_validation['valid']:
                await ws.send_message(json.dumps(result_of_validation['errors']))
                continue

            current_location = json.loads(current_location)
            bus_id = current_location['busId']

            if bus_id in BUSES:
                bus = BUSES[bus_id]
                bus.update(current_location['lat'], current_location['lng'])
            else:
                BUSES[bus_id] = Bus(
                    busId=bus_id,
                    lat=current_location['lat'],
                    lng=current_location['lng'],
                    route=current_location['route']
                )

        except ConnectionClosed:
            break


async def start_server(bus_port, browser_port, v):
    if v:
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('trio-websocket').setLevel(logging.CRITICAL)
    else:
        logging.disable(logging.CRITICAL)

    serve_websocket_with_ssl_contex = partial(serve_websocket, ssl_context=None)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket_with_ssl_contex, update_current_location, '127.0.0.1', bus_port)
        nursery.start_soon(serve_websocket_with_ssl_contex, talk_to_browser, '127.0.0.1', browser_port)


@click.command()
@click.option('-bus', '--bus_port', type=int, default=8080, required=False, help="port for the bus simulator")
@click.option('-browser', '--browser_port', type=int, default=8000, required=False, help="Browser port")
@click.option('-v', '--v', type=bool, default=False, required=False, help="Turn on logging")
async def main(bus_port, browser_port, v):
    await start_server(bus_port, browser_port, v)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):  # FIXME catch this error
        trio.run(main.main)
