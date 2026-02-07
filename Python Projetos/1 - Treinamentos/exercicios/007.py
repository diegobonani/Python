# NOTAS COM ARRAY POR DIEGO BONANI

n = []
n1 = float(input("Digite a nota 1"))
n2 = float(input("Digite a nota 2"))
n3 = float(input("Digite a nota 3"))
n4 = float(input("Digite a nota 4"))
n.append(n1)
n.append(n2)
n.append(n3)
n.append(n4)
res = sum(n) / len(n)
print("A 1º nota {}, A 2ª Nota {} A 3ª Nota {}, A 4ª Nota {} Gerou numa média de {}".format(n1,n2,n3,n4,res))