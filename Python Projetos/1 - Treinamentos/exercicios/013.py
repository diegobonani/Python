#GRAUS FAREHINT PARA CELSIUS

#C = 5 * ((F-32) / 9).
    F = eval(input("Digite o valor do Grau em farehint"))
    Aux1 = F - 32
    Aux2 = Aux1 / 9
    c = Aux2 * 5
    print("O valor do graus em CELSIUS é {}".format(c))