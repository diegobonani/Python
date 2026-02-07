from datetime import date

ano = int(input("Descubra se o ano é bissexto"))

try:
    if(ano == 0):
        print("O ano marcado foi de {}".format(date.today().year))
    else:
        if(ano % 4 == 0 and ano % 100 != 0 or ano % 400 == 0):
            print("{} é um ano bissexto".format(ano))
        else:
            print("{} o ano não é bissexto".format(ano))
except:
    print("Erro ocorrido")