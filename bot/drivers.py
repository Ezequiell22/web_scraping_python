import pyodbc

# Listar todos os drivers ODBC disponíveis
drivers = pyodbc.drivers()

# Imprimir a lista de drivers
print(drivers)
