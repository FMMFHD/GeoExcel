

def convertToKnownDatatype(datatype):
    """
        Convert the name of the data type to a conventional name
    """

    if datatype == 'geography':
        return "geography(POINT)"
    elif datatype == 'float8':
        return "Float"
    elif datatype == 'int4':
        return "Int"
    elif datatype == 'varchar':
        return "VARCHAR(255)"
    else:
        return datatype


def checkPointType(number, typ):
    """
        Return a point in decimal form
    """
    if typ == 'degree':
        return convertDegreeToDecimal(number)
    elif typ == 'decimal':
        return number

def convertDegreeToDecimal(number):
    """
    Converte graus,minutos,segundos para um valor decimal
    """
    if len(number.split("-")) == 1:
        positive = True
    else:
        positive = False

    split = number.split("\u00b0")
    d = float(split[0])    #Degree
    split = split[1].split("'")
    m = float(split[0])   #minute
    s = float(split[1].split('"')[0])  #second
    if positive:
        return d + (m/60) + (s/3600)
    else:
        return -1*(-1*d + (m/60) + (s/3600))

def convertDecimalToDegree(number):
    """
    Converte um valor decimal para um valor em graus,minutos,segundos
    """
    if number < 0:
        negative = True
        number *=-1
    else:
        negative = False
    d = int(number)
    m = int((number-d)*60)
    s = round((number-d-m/60)*3600)
    if negative:
        return "-%d\u00b0%s'%s''"%(d,convertNumtoStr(m),convertNumtoStr(s))
    else:
        return "%d\u00b0%s'%s''"%(d,convertNumtoStr(m),convertNumtoStr(s))

def convertNumtoStr(number):
    if number < 10:
        return "0%d"%(number)
    else:
        return "%d"%(number)