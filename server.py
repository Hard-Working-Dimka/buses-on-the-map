import json
import logging
from dataclasses import dataclass, asdict
from functools import partial

import trio
import trio_websocket
from trio_websocket import serve_websocket, ConnectionClosed

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


async def main():
    serve_websocket_with_ssl_contex = partial(serve_websocket, ssl_context=None)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket_with_ssl_contex, update_current_location, '127.0.0.1', 8080)
        nursery.start_soon(serve_websocket_with_ssl_contex, talk_to_browser, '127.0.0.1', 8000)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('trio-websocket').setLevel(logging.CRITICAL)

    trio.run(main)
