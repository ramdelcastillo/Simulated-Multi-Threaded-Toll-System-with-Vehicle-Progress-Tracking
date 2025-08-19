import socket, threading, json, time, os, string, random
from datetime import datetime
from multiprocessing import Lock

IP = "10.2.11.80"
PORT = 8080
ADDR = (IP, PORT)
SIZE = 1024
FORMAT = "utf-8"
DISCONNECT_MSG = "!DISCONNECT"
ENTRY_EXIT_LOGS = "/home/g10/entryAndExitLogs.json"
SAVED_FEES_VEHICLES_PROCESSED = "/home/g10/savedTotalFeesAndVehiclesProcessed.json"

class TollSystemServer:
    _instance = None
    def __init__(self, ip=IP, port=PORT, size=SIZE, format=FORMAT):
        if TollSystemServer._instance is not None:
            raise Exception("This class is a singleton!")
        TollSystemServer._instance = self

        self.IP = ip
        self.PORT = port
        self.ADDR = (self.IP, self.PORT)
        self.SIZE = size
        self.FORMAT = format
        self.server = None
        self.clientConnections = []
        self.highwayStatsETAModule = HighwayStatisticsAndETAModule()
        self.loggingLock = Lock()

    @staticmethod
    def getInstance() -> "TollSystemServer":
        if TollSystemServer._instance is None:
            TollSystemServer()
        return TollSystemServer._instance

    def startCommandLineInterface(self):
        def commandLoop():
            while True:
                cmd = input("TollSystemServer> ").strip().lower()
                if cmd == "s":
                    stats = self.highwayStatsETAModule.generateRealtimeStats()
                    print("")
                elif cmd == "v":
                    stats = self.highwayStatsETAModule.printVehicleStatuses()
                    print("")
                else:
                    print("")

        cliThread = threading.Thread(target=commandLoop, daemon=True)
        cliThread.start()

    def startTollSystemServer(self):
        print("Toll System Server is starting...")
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(self.ADDR)

    def acceptIncomingTollClientConnections(self):
        self.server.listen()
        print(f"Toll System Server is listening on {IP}:{PORT}")

    def stopTollSystemServer(self):
        print("Stopping toll system server...")
        for client in self.clientConnections:
            try:
                client.send(DISCONNECT_MSG.encode(self.FORMAT))
                client.close()
            except:
                pass
        self.server.close()
        print("Server and all client connections closed.")

    def createClientConnectionThreads(self):
        try:
            while True:
                conn, addr = self.server.accept()
                self.clientConnections.append(conn)
                thread = threading.Thread(target=self.handleClientConnection, args=(conn, addr))
                thread.start()
                print(f"\rActive Connections: {len(self.clientConnections)}\nTollSystemServer> ", end="")
        except KeyboardInterrupt:
            self.stopTollSystemServer()

    def handleClientConnection(self, conn, addr):
        connected = True

        while connected:
            try:
                msg = conn.recv(self.SIZE).decode(self.FORMAT)

                data = json.loads(msg)

                if data.get("type") == "keepalive":
                    continue

                self.processEntry(data, addr[1])

                conn.send("Data received successfully.".encode(self.FORMAT))

            except (ConnectionResetError, BrokenPipeError):
                break
            except Exception as e:
                break

        if conn in self.clientConnections:
            self.clientConnections.remove(conn)
        conn.close()
        print(f"\rActive Connections: {len(self.clientConnections)}\nTollSystemServer> ", end="")

    def processEntry(self, data, port):
        enteredFrom = data.get("enteredFrom", "N/A")
        plateNumber = data.get("plateNumber", "N/A")
        enteredAt = data.get("enteredAt", "N/A")
        action = data.get("action", "N/A")
        intendedExit = data.get("intendedExit", "N/A")
        time, tollFee = self.highwayStatsETAModule.calculateEtaAndTollFee(enteredFrom, intendedExit)
        transactionID = self.generateRandomTransactionID(port)
        data["estimatedTime"] = time
        data["tollFee"] = tollFee
        data["transactionID"] = transactionID

        if time != 0 and tollFee != 0:
            self.logEntryOrExit(data)
            vehicle = Vehicle(plateNumber, enteredFrom, intendedExit, travelDuration=time, enteredAt=enteredAt, currentTransactionID=transactionID, tollFee=tollFee)
            self.highwayStatsETAModule.addVehicle(vehicle)

    def logEntryOrExit(self, data):
        with self.loggingLock:
            with open(ENTRY_EXIT_LOGS, 'r') as logFile:
                logData = json.load(logFile)

            logData.append(data)

            with open(ENTRY_EXIT_LOGS, 'w') as logFile:
                json.dump(logData, logFile, indent=4)


    def generateRandomTransactionID(self, port):
        characters = string.ascii_uppercase + string.digits  # A-Z and 0-9
        transactionID = ''.join(random.choice(characters) for i in range(10))
        return f"{transactionID}-{port}"

class HighwayStatisticsAndETAModule:
    def __init__(self):
        data = self.loadData()
        self.vehiclesOnHighway = 0
        self.totalVehiclesProcessed = data.get("totalVehiclesProcessed")
        self.totalVehiclesExited = 0
        self.totalFeesCollected = data.get("totalFeesCollected")
        self.inTransitVehiclesList = []
        self.exitedVehiclesList = []
        self.vehicleLock = Lock()
        self.updateFeesLock = Lock()
        self.removeVehicleLock = Lock()

    def loadData(self):
        try:
            with open(SAVED_FEES_VEHICLES_PROCESSED, 'r') as file:
                data = json.load(file)
                return data
        except FileNotFoundError:
            return {"totalFeesCollected": 0, "totalVehiclesProcessed": 0}

    def updateTotalFeesCollected(self, tollFee):
        with self.updateFeesLock:
            self.totalFeesCollected += tollFee
            self.totalVehiclesProcessed += 1

            data = {
                "totalFeesCollected": self.totalFeesCollected,
                "totalVehiclesProcessed": self.totalVehiclesProcessed
            }
            with open(SAVED_FEES_VEHICLES_PROCESSED, 'w') as file:
                json.dump(data, file, indent=4)

    def generateRealtimeStats(self):
        output = (
            f"Total Vehicles on the Highway: {self.vehiclesOnHighway}\n"
            f"Total Vehicles Exited: {self.totalVehiclesExited}\n"
            f"Total Vehicles Processed: {self.totalVehiclesProcessed}\n"
            f"Total Fees Collected: Php {self.totalFeesCollected}"
        )
        print(output)

    def calculateEtaAndTollFee(self, entryPoint, exitPoint):
        time = 0
        tollFee = 0

        if "tollplaza-north-entry-booth-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[:8]):  # 'a' to 'h', a = 0
                if f"regular-north-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-north-exit-booth-" in exitPoint:
                    time = 6 + (8 * 6)
                    tollFee = 50 + (8 * 10)

        elif "regular-north-entry-booth-a-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[1:8]):  # 'b' to 'h', b = 0
                if f"regular-north-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-north-exit-booth-" in exitPoint:
                    time = 6 + (7 * 6)
                    tollFee = 50 + (7 * 10)

        elif "regular-north-entry-booth-b-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[2:8]):  # 'c' to 'h', c = 0
                if f"regular-north-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-north-exit-booth-" in exitPoint:
                    time = 6 + (6 * 6)
                    tollFee = 50 + (6 * 10)

        elif "regular-north-entry-booth-c-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[3:8]):  # 'd' to 'h', d = 0
                if f"regular-north-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-north-exit-booth-" in exitPoint:
                    # Exit after 'h'
                    time = 6 + (5 * 6)  # i = 5
                    tollFee = 50 + (5 * 10)  # i = 5

        elif "regular-north-entry-booth-d-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[4:8]):  # 'e' to 'h', e = 0
                if f"regular-north-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-north-exit-booth-" in exitPoint:
                    time = 6 + (4 * 6)
                    tollFee = 50 + (4 * 10)

        elif "regular-north-entry-booth-e-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[5:8]):  # 'f' to 'h', f = 0
                if f"regular-north-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-north-exit-booth-" in exitPoint:
                    time = 6 + (3 * 6)
                    tollFee = 50 + (3 * 10)

        elif "regular-north-entry-booth-f-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[6:8]):  # 'g' to 'h', g = 0
                if f"regular-north-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-north-exit-booth-" in exitPoint:
                    time = 6 + (2 * 6)
                    tollFee = 50 + (2 * 10)

        elif "regular-north-entry-booth-g-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[7:8]):  # 'h', h = 0
                if f"regular-north-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-north-exit-booth-" in exitPoint:
                    time = 6 + (1 * 6)
                    tollFee = 50 + (1 * 10)

        elif "regular-north-entry-booth-h-" in entryPoint:
            if "tollplaza-north-exit-booth-" in exitPoint:
                time = 6
                tollFee = 50

        elif "tollplaza-south-entry-booth-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[:8]):  # 'a' to 'h', a = 0
                if f"regular-south-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-south-exit-booth-" in exitPoint:
                    time = 6 + (8 * 6)
                    tollFee = 50 + (8 * 10)

        elif "regular-south-entry-booth-a-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[1:8]):  # 'b' to 'h', b = 0
                if f"regular-south-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-south-exit-booth-" in exitPoint:
                    time = 6 + (7 * 6)
                    tollFee = 50 + (7 * 10)

        elif "regular-south-entry-booth-b-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[2:8]):  # 'c' to 'h', c = 0
                if f"regular-south-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-south-exit-booth-" in exitPoint:
                    time = 6 + (6 * 6)
                    tollFee = 50 + (6 * 10)

        elif "regular-south-entry-booth-c-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[3:8]):  # 'd' to 'h', d = 0
                if f"regular-south-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-south-exit-booth-" in exitPoint:
                    time = 6 + (5 * 6)
                    tollFee = 50 + (5 * 10)

        elif "regular-south-entry-booth-d-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[4:8]):  # 'e' to 'h', e = 0
                if f"regular-south-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-south-exit-booth-" in exitPoint:
                    time = 6 + (4 * 6)
                    tollFee = 50 + (4 * 10)

        elif "regular-south-entry-booth-e-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[5:8]):  # 'f' to 'h', f = 0
                if f"regular-south-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-south-exit-booth-" in exitPoint:
                    time = 6 + (3 * 6)
                    tollFee = 50 + (3 * 10)

        elif "regular-south-entry-booth-f-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[6:8]):  # 'g' to 'h', g = 0
                if f"regular-south-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-south-exit-booth-" in exitPoint:
                    time = 6 + (2 * 6)
                    tollFee = 50 + (2 * 10)

        elif "regular-south-entry-booth-g-" in entryPoint:
            for i, letter in enumerate(string.ascii_lowercase[7:8]):  # 'h', h = 0
                if f"regular-south-exit-booth-{letter}-" in exitPoint:
                    time = 6 + (i * 6)
                    tollFee = 50 + (i * 10)
                    break
            else:
                if "tollplaza-south-exit-booth-" in exitPoint:
                    time = 6 + (1 * 6)
                    tollFee = 50 + (1 * 10)

        elif "regular-south-entry-booth-h-" in entryPoint:
            if "tollplaza-south-exit-booth-" in exitPoint:
                time = 6
                tollFee = 50
        else:
            time = 0
            tollFee = 0

        return time, tollFee

    def addVehicle(self, vehicle):
        with self.vehicleLock:
            self.inTransitVehiclesList.append(vehicle)
            self.vehiclesOnHighway += 1

    def removeVehicle(self, plateNumber):
        with self.removeVehicleLock:
            for vehicle in self.inTransitVehiclesList:
                if vehicle.plateNumber == plateNumber:
                    self.inTransitVehiclesList.remove(vehicle)
                    self.exitedVehiclesList.append(vehicle)
                    self.vehiclesOnHighway -= 1
                    self.totalVehiclesExited += 1
                    break

    def printVehicleStatuses(self):
        tollSystemServer = TollSystemServer.getInstance()
        status_str = f"Active Connections: {len(tollSystemServer.clientConnections)}\n"
        status_str += "------------------------------\n"
        status_str += "Vehicles in transit:\n"
        status_str += f"{'plateNumber':<12} {'entryPoint':<30} {'intendedExit':<30} {'vehicleState':<12} {'elapsedTime':<12} {'remainingTime':<14} {'enteredAt':<20} {'progress':<10}\n"

        for vehicle in self.inTransitVehiclesList:
            status_str += f"{vehicle.getPlateNumber():<12} {vehicle.getEntryPoint():<30} {vehicle.getIntendedExit():<30} {vehicle.getVehicleState():<12} {vehicle.getElapsedTime():<12} {vehicle.getRemainingTime():<14} {vehicle.getEnteredAt():<20} {vehicle.getProgress():<10}%\n"

        status_str += "\nVehicles exited:\n"
        status_str += f"{'plateNumber':<12} {'entryPoint':<30} {'intendedExit':<30} {'vehicleState':<12} {'elapsedTime':<12} {'remainingTime':<14} {'arrivedAt':<20} {'exitedAt':<20}\n"

        for vehicle in self.exitedVehiclesList:
            status_str += f"{vehicle.getPlateNumber():<12} {vehicle.getEntryPoint():<30} {vehicle.getIntendedExit():<30} {vehicle.getVehicleState():<12} {vehicle.getElapsedTime():<12} {vehicle.getRemainingTime():<14} {vehicle.getEnteredAt():<20} {vehicle.getExitedAt():<20}\n"

        status_str += "------------------------------"
        print(status_str)

class Vehicle:
    def __init__(self, plateNumber, entryPoint, intendedExit, travelDuration, enteredAt, currentTransactionID, tollFee):
        self.plateNumber = plateNumber
        self.currentTransactionID = currentTransactionID
        self.entryPoint = entryPoint
        self.intendedExit = intendedExit
        self.travelDuration = travelDuration
        self.elapsedTime = 0
        self.progress = 0
        self.remainingTime = travelDuration
        self.vehicleState = "In Transit"
        self.enteredAt = enteredAt
        self.exitedAt = None
        self.tollFee = tollFee
        self.movingThread = threading.Thread(target=self.moveVehicle)
        self.movingThread.start()

    def moveVehicle(self):
        tollSystemServer = TollSystemServer.getInstance()
        for i in range(self.travelDuration):
            time.sleep(1)
            self.elapsedTime = i + 1
            self.progress = round(((i + 1) / self.travelDuration) * 100)
            self.remainingTime = self.travelDuration - (i + 1)

        if(self.progress == 100):
            self.vehicleState = "Exited"
            self.exitedAt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            tollSystemServer.highwayStatsETAModule.removeVehicle(self.plateNumber)
            tollSystemServer.highwayStatsETAModule.updateTotalFeesCollected(self.tollFee)
            data = {}
            data["enteredFrom"] = self.getEntryPoint()
            data["plateNumber"] = self.getPlateNumber()
            data["exitedAt"] = self.getExitedAt()
            data["action"] = "exit"
            data["intendedExit"] = self.getIntendedExit()
            data["estimatedTime"] = self.getTravelDuration()
            data["tollFee"] = self.getTollFee()
            data["transactionID"] = self.getCurrentTransactionID()
            tollSystemServer.logEntryOrExit(data)
    def getPlateNumber(self):
        return self.plateNumber

    def getCurrentTransactionID(self):
        return self.currentTransactionID

    def getEntryPoint(self):
        return self.entryPoint

    def getIntendedExit(self):
        return self.intendedExit

    def getTravelDuration(self):
        return self.travelDuration

    def getElapsedTime(self):
        return self.elapsedTime

    def getProgress(self):
        return self.progress

    def getRemainingTime(self):
        return self.remainingTime

    def getVehicleState(self):
        return self.vehicleState

    def getEnteredAt(self):
        return self.enteredAt

    def getExitedAt(self):
        return self.exitedAt

    def getTollFee(self):
        return self.tollFee



def main():
    tollSystemServer = TollSystemServer()
    tollSystemServer.startTollSystemServer()
    tollSystemServer.acceptIncomingTollClientConnections()
    tollSystemServer.startCommandLineInterface()
    tollSystemServer.createClientConnectionThreads()

if __name__ == "__main__":
    main()
