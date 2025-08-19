import socket, json, threading, time, random, string, multiprocessing, re
from datetime import datetime

IP = socket.gethostbyname("ccscloud.dlsu.edu.ph")
PORT = 31200
ADDR = (IP, PORT)
SIZE = 1024
FORMAT = "utf-8"
DISCONNECT_MSG = "!DISCONNECT"

entryBooths = [
    # North Entry Booths
    "tollplaza-north-entry-booth-1", "tollplaza-north-entry-booth-2", "tollplaza-north-entry-booth-3",
    "regular-north-entry-booth-a-1", "regular-north-entry-booth-a-2",
    "regular-north-entry-booth-b-1", "regular-north-entry-booth-b-2",
    "regular-north-entry-booth-c-1", "regular-north-entry-booth-c-2",
    "regular-north-entry-booth-d-1", "regular-north-entry-booth-d-2",
    "regular-north-entry-booth-e-1", "regular-north-entry-booth-e-2",
    "regular-north-entry-booth-f-1", "regular-north-entry-booth-f-2",
    "regular-north-entry-booth-g-1", "regular-north-entry-booth-g-2",
    "regular-north-entry-booth-h-1", "regular-north-entry-booth-h-2",

    # South Entry Booths
    "tollplaza-south-entry-booth-1", "tollplaza-south-entry-booth-2", "tollplaza-south-entry-booth-3",
    "regular-south-entry-booth-a-1", "regular-south-entry-booth-a-2",
    "regular-south-entry-booth-b-1", "regular-south-entry-booth-b-2",
    "regular-south-entry-booth-c-1", "regular-south-entry-booth-c-2",
    "regular-south-entry-booth-d-1", "regular-south-entry-booth-d-2",
    "regular-south-entry-booth-e-1", "regular-south-entry-booth-e-2",
    "regular-south-entry-booth-f-1", "regular-south-entry-booth-f-2",
    "regular-south-entry-booth-g-1", "regular-south-entry-booth-g-2",
    "regular-south-entry-booth-h-1", "regular-south-entry-booth-h-2"
]

exitBooths = [
    # North Entry Booths
    "regular-north-exit-booth-a-1", "regular-north-exit-booth-a-2",
    "regular-north-exit-booth-b-1", "regular-north-exit-booth-b-2",
    "regular-north-exit-booth-c-1", "regular-north-exit-booth-c-2",
    "regular-north-exit-booth-d-1", "regular-north-exit-booth-d-2",
    "regular-north-exit-booth-e-1", "regular-north-exit-booth-e-2",
    "regular-north-exit-booth-f-1", "regular-north-exit-booth-f-2",
    "regular-north-exit-booth-g-1", "regular-north-exit-booth-g-2",
    "regular-north-exit-booth-h-1", "regular-north-exit-booth-h-2",
    "tollplaza-north-exit-booth-1", "tollplaza-north-exit-booth-2", "tollplaza-north-exit-booth-3",

    # South Entry Booths
    "regular-south-exit-booth-a-1", "regular-south-exit-booth-a-2",
    "regular-south-exit-booth-b-1", "regular-south-exit-booth-b-2",
    "regular-south-exit-booth-c-1", "regular-south-exit-booth-c-2",
    "regular-south-exit-booth-d-1", "regular-south-exit-booth-d-2",
    "regular-south-exit-booth-e-1", "regular-south-exit-booth-e-2",
    "regular-south-exit-booth-f-1", "regular-south-exit-booth-f-2",
    "regular-south-exit-booth-g-1", "regular-south-exit-booth-g-2",
    "regular-south-exit-booth-h-1", "regular-south-exit-booth-h-2",
    "tollplaza-south-exit-booth-1", "tollplaza-south-exit-booth-2", "tollplaza-south-exit-booth-3"
]

random.shuffle(entryBooths)
random.shuffle(exitBooths)

entryBoothsGroup1 = [
    "tollplaza-north-entry-booth-1", "tollplaza-north-entry-booth-2", "tollplaza-north-entry-booth-3",
    "regular-north-entry-booth-a-1", "regular-north-entry-booth-a-2",
    "regular-north-entry-booth-b-1", "regular-north-entry-booth-b-2",
    "regular-north-entry-booth-c-1", "regular-north-entry-booth-c-2",
]

entryBoothsGroup2 = [
    "regular-north-entry-booth-d-1", "regular-north-entry-booth-d-2",
    "regular-north-entry-booth-e-1", "regular-north-entry-booth-e-2",
    "regular-north-entry-booth-f-1", "regular-north-entry-booth-f-2",
    "regular-north-entry-booth-g-1", "regular-north-entry-booth-g-2",
    "regular-north-entry-booth-h-1", "regular-north-entry-booth-h-2",
]

entryBoothsGroup3 = [
    "tollplaza-south-entry-booth-1", "tollplaza-south-entry-booth-2", "tollplaza-south-entry-booth-3",
    "regular-south-entry-booth-a-1", "regular-south-entry-booth-a-2",
    "regular-south-entry-booth-b-1", "regular-south-entry-booth-b-2",
    "regular-south-entry-booth-c-1", "regular-south-entry-booth-c-2",
]

entryBoothsGroup4 = [
    "regular-south-entry-booth-d-1", "regular-south-entry-booth-d-2",
    "regular-south-entry-booth-e-1", "regular-south-entry-booth-e-2",
    "regular-south-entry-booth-f-1", "regular-south-entry-booth-f-2",
    "regular-south-entry-booth-g-1", "regular-south-entry-booth-g-2",
    "regular-south-entry-booth-h-1", "regular-south-entry-booth-h-2",
]

random.shuffle(entryBoothsGroup1)
random.shuffle(entryBoothsGroup2)
random.shuffle(entryBoothsGroup3)
random.shuffle(entryBoothsGroup4)

allBoothGroups = [entryBoothsGroup1, entryBoothsGroup2, entryBoothsGroup3, entryBoothsGroup4]
# CAN BE USED IN ANOTHER VM/PC TO SIMULATE MULTIPLE CONNECTIONS
# allBoothGroups = [entryBoothsGroup1, entryBoothsGroup2] PC1 (THIS PC)
# allBoothGroups = [entryBoothsGroup3, entryBoothsGroup4] PC2 (OTHER PC)

def getValidExits(entryBooth, exitBooths):
    match = re.match(r"regular-(north|south)-entry-booth-([a-h])-", entryBooth)
    if match:
        direction = match.group(1)
        boothLetter = match.group(2)
        validExits = []
        for exitBooth in exitBooths:
            if f"-{direction}-" not in exitBooth:
                continue
            letterMatch = re.search(fr"regular-{direction}-exit-booth-([a-h])-", exitBooth)
            if letterMatch:
                exitLetter = letterMatch.group(1)
                if exitLetter <= boothLetter:
                    continue
            validExits.append(exitBooth)
    else:
        if "north" in entryBooth:
            direction = "north"
        else:
            direction = "south"
        validExits = [
            exitBooth for exitBooth in exitBooths
            if f"-{direction}-" in exitBooth
        ]

    return validExits

def generateRandomPlate():
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=3))
    return letters + numbers

def sendKeepalive(client, stopEvent):
    while not stopEvent.is_set():
        time.sleep(30)
        try:
            keepaliveMsg = json.dumps({"type": "keepalive"})
            client.send(keepaliveMsg.encode(FORMAT))
        except Exception as e:
            print(f"[KEEPALIVE ERROR] {e}")
            break

def simulateClientForGroup(groupIndex, group, pipeConn):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((IP, PORT))

        stopEvent = threading.Event()
        threading.Thread(target=sendKeepalive, args=(client, stopEvent), daemon=True).start()

        while True:
            if pipeConn.poll():
                msg = pipeConn.recv()

                if msg == DISCONNECT_MSG:
                    client.send(DISCONNECT_MSG.encode(FORMAT))
                    stopEvent.set()
                    break

                if msg == "get_booth":
                    boothId = random.choice(group)
                    plateNumber = generateRandomPlate()
                    entryData = {
                        "boothId": boothId,
                        "plateNumber": plateNumber
                    }
                    pipeConn.send(entryData)
                    continue

                if isinstance(msg, dict) and msg.get("type") == "entry_data":
                    boothId = msg["boothId"]
                    intendedExit = msg["intendedExit"]

                    entryData = {
                        "enteredFrom": boothId,
                        "plateNumber": plateNumber,
                        "enteredAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "action": "entry",
                        "intendedExit": intendedExit
                    }

                    try:
                        client.send(json.dumps(entryData).encode(FORMAT))
                        response = client.recv(SIZE).decode(FORMAT)
                    except Exception as e:
                        print(f"Group {groupIndex + 1} - [{boothId}] Error during send/receive: {e}")
                        stopEvent.set()
                        break

    except Exception as e:
        print(f"Group {groupIndex + 1} Connection error: {e}")
    finally:
        client.close()
        pipeConn.close()
        print(f"Group {groupIndex + 1} Client shutdown.")

def main():
    processes = []
    boothPipes = []

    for groupIndex, group in enumerate(allBoothGroups):
        parent, child = multiprocessing.Pipe()
        boothPipes.append(parent)
        p = multiprocessing.Process(target=simulateClientForGroup, args=(groupIndex, group, child))
        p.start()
        processes.append(p)

    entry = None

    while True:
        currentBooth = random.randint(0, 3)
        # CAN BE USED IN ANOTHER VM/PC TO SIMULATE MULTIPLE CONNECTIONS
        # currentBooth = random.randint(0, 1) PC1 (THIS PC)
        # currentBooth = random.randint(0, 1) PC2 (OTHER PC)

        print(f"Interacting with entries from Group {currentBooth + 1}.")

        # CAN BE USED IN ANOTHER VM/PC TO SIMULATE MULTIPLE CONNECTIONS
        # print(f"Interacting with entries from Group {currentBooth + 1}.") (THIS PC)
        # print(f"Interacting with entries from Group {currentBooth + 3}.") (OTHER PC)

        boothPipe = boothPipes[currentBooth]
        boothPipe.send("get_booth")

        entry = boothPipe.recv()
        print(f"Received entry: Booth: {entry['boothId']}, Plate Number: {entry['plateNumber']}")

        validExits = getValidExits(entry["boothId"], exitBooths)
        print(f"Valid exits for {entry['boothId']}: {validExits}")

        intendedExit = random.choice(validExits)
        print(f"Selected exit: {intendedExit}")

        boothPipe.send({
            "type": "entry_data",
            "boothId": entry['boothId'],
            "intendedExit": intendedExit
        })
        print(f"Exit sent for booth {entry['boothId']}: {intendedExit}")
        print("")

        time.sleep(5)

    for pipe in boothPipes:
        pipe.send(DISCONNECT_MSG)

    for p in processes:
        p.join()

    print("All booth clients closed.")

if __name__ == "__main__":
    main()
