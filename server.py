import json
import logging
from functools import partial

import trio
import trio_websocket
from trio_websocket import serve_websocket, ConnectionClosed

BUSES = {}


async def listen_browser(ws, send_channel):
    while True:
        try:
            response = await ws.get_message()
            logging.debug(response)
            bounds = json.loads(response)
            await send_channel.send(bounds)
            await trio.sleep(5)
        except trio_websocket.ConnectionClosed:
            break


async def send_new_location(ws, receive_channel):
    bounds = None
    while True:
        try:
            with trio.move_on_after(0.1) as move:
                bounds = await receive_channel.receive()

        except trio.Cancelled:
            pass
        if not bounds:
            continue

        try:
            buses_location = {
                "msgType": "Buses",
                "buses": [

                ]
            }

            for bus_id, bus_data in BUSES.items():
                if is_inside(bounds['data'], bus_data['lat'], bus_data['lng'], ):
                    buses_location['buses'].append(
                        {
                            "busId": bus_id,
                            "lat": bus_data['lat'],
                            "lng": bus_data['lng'],
                            "route": bus_data['route']
                        }
                    )

            buses_location = json.dumps(buses_location)
            await ws.send_message(buses_location)
            await trio.sleep(0.1)
        except ConnectionClosed:
            break


async def talk_to_browser(request):
    send_channel, receive_channel = trio.open_memory_channel(0)
    ws = await request.accept()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(listen_browser, ws, send_channel)
        nursery.start_soon(send_new_location, ws, receive_channel)


def is_inside(bounds, lat, lng):
    s_lat = bounds['south_lat']
    n_lng = bounds['north_lat']
    w_lng = bounds['west_lng']
    e_lng = bounds['east_lng']

    return (s_lat <= lat) and (lat <= n_lng) and (w_lng <= lng) and (lng <= e_lng)


async def update_current_location(request):
    ws = await request.accept()
    while True:
        try:
            current_location = await ws.get_message()
            current_location = json.loads(current_location)

            BUSES[current_location['busId']] = {
                'lat': current_location['lat'],
                'lng': current_location['lng'],
                'route': current_location['route'],
            }

            # print(current_location) TODO add to logger
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
