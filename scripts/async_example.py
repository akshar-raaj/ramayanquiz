import asyncio
import aiohttp

"""
Coroutines are Python functions that can be suspended and resumed at any time.

This is different from a subroutine which have a single entry and exit point.

Coroutines are identified with their usage of async/await keywords.
"""


# Create a coroutine function
async def double(num):
    # Mimic a long-running operation for 1 second
    await asyncio.sleep(1)
    return num * 2

# This is invalid as double is not a subroutine/function and is instead a coroutine
# double(5)

# Need to call double using asyncio.Run
# Passing the coroutine function is not sufficient
# The coroutine object needs to be passed
# print(asyncio.run(double(5)))


# We can write another coroutine that uses a coroutine function
# As we have an awaitable use inside this function, thus it must be marked `async`
async def use_num(num):
    # As we are using a coroutine, hence we need to await it.
    # Writing return double(num) is invalid
    return await double(num)

print(asyncio.run(use_num(5)))


async def say_something(something, delay):
    print(f"Will print {something}")
    await asyncio.sleep(delay)
    print(f"{something} World!")


async def make_request(url):
    print(f"making request to {url}")
    async with aiohttp.ClientSession() as session:
        print(f"created session to {url}")
        async with await session.get(url) as reponse:
            print(f"received response from {url}")
            content = await reponse.text()
            print(f"received text from {url}", content[:100])
            return content


async def main():
    things = ['hello', 'hola', 'namaste']
    print("combining")
    somethings = [say_something(thing, len(thing)) for thing in things]
    print("combined")
    await asyncio.gather(*somethings)


async def requests():
    urls = ['http://awsquiz.net', 'http://ramayanquiz.com']
    make_requests = [make_request(url) for url in urls]
    await asyncio.gather(*make_requests)


# asyncio.run(main())
# asyncio.run(requests())
