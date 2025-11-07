import json

import pytest
import trio
from trio_websocket import open_websocket_url

from server import start_server


@pytest.mark.trio
async def test_bus_server_validation():
    bus_port = 8080
    browser_port = 8000

    async with trio.open_nursery() as nursery:
        nursery.start_soon(start_server, bus_port, browser_port, True)
        await trio.sleep(3)

        async with open_websocket_url(f'ws://127.0.0.1:{bus_port}') as ws:
            data = {
                "busId": 123,
                "lat": 55.75,
                "lng": 37.61,
                "route": "42"
            }
            await ws.send_message(json.dumps(data))
            await trio.sleep(5)

            server_response = await ws.get_message()
            server_response = json.loads(server_response)
            assert server_response == ["[busId] --- The type is incorrect, it must be a string."]

            data = {
                "busId": "123",
                "lat": 55.75,
                "route": "42"
            }
            await ws.send_message(json.dumps(data))
            await trio.sleep(5)

            server_response = await ws.get_message()
            server_response = json.loads(server_response)
            assert server_response == ["[lng] --- You forgot to specify the longitude!"]

            data = {
                "busId": 123,
                "lat": 55.75,
                "route": "42"
            }
            await ws.send_message(json.dumps(data))
            await trio.sleep(5)

            server_response = await ws.get_message()
            server_response = json.loads(server_response)
            assert server_response == ["[busId] --- The type is incorrect, it must be a string.",
                                       "[lng] --- You forgot to specify the longitude!"]

            data = 'lalala'
            await ws.send_message(data)
            await trio.sleep(5)

            server_response = await ws.get_message()
            server_response = json.loads(server_response)
            assert server_response == ["Requires valid JSON"]

        nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_browser_server_validation():
    bus_port = 8080
    browser_port = 8000

    async with trio.open_nursery() as nursery:
        nursery.start_soon(start_server, bus_port, browser_port, True)
        await trio.sleep(3)

        async with open_websocket_url(f'ws://127.0.0.1:{browser_port}') as ws:
            data = {
                "data": {
                    "south_lat": 55.71676518024585,
                    "north_lat": 55.76281277802112,
                    "west_lng": 37.605772018432624,
                    "east_lng": 37.764816284179695
                }
            }
            await ws.send_message(json.dumps(data))
            await trio.sleep(5)
            while True:
                server_response = await ws.get_message()
                response = json.loads(server_response)
                if isinstance(response, list):
                    break
            assert response == ['[msgType] --- You forgot to specify the message type or put it in the wrong place!']

            data = {
                "msgType": "newBounds",
                "data": {
                    "north_lat": 55.76281277802112,
                    "west_lng": 37.605772018432624,
                    "east_lng": 37.764816284179695
                }
            }
            await ws.send_message(json.dumps(data))
            await trio.sleep(5)
            while True:
                server_response = await ws.get_message()
                response = json.loads(server_response)
                if isinstance(response, list):
                    break
            assert response == ["[data.south_lat] --- Missing required field!"]

            data = {
                "msgType": "newBounds",
                "data": {
                    "north_lat": "55.76281277802112",
                    "west_lng": 37.605772018432624,
                    "east_lng": 37.764816284179695
                }
            }
            await ws.send_message(json.dumps(data))
            await trio.sleep(5)
            while True:
                server_response = await ws.get_message()
                response = json.loads(server_response)
                if isinstance(response, list):
                    break
            assert response == ["[data.south_lat] --- Missing required field!",
                                "[data.north_lat] --- Invalid type: expected float."]

            data = 'lalala'
            await ws.send_message(data)
            await trio.sleep(5)
            while True:
                server_response = await ws.get_message()
                response = json.loads(server_response)
                if isinstance(response, list):
                    break
            assert response == ["Requires valid JSON"]

        nursery.cancel_scope.cancel()
