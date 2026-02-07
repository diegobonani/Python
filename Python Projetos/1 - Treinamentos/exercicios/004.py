#Manipulando variável por Diego Bonani

nome = input("Digite algo qualquer:")
print("Tipo:" , type(nome)) 
print("Tem espaço?" , nome.isspace())
print("É um número?" , nome.isnumeric()) 
print("É alfabético" , nome.isalpha()) 
print("É alfanumérico" , nome.isalnum()) 
print("Está em maiuscula" , nome.isupper()) 
print("Está em minuscula" , nome.islower()) 
print("Está capitalizada?" , nome.capitalize())

''' OU MANIPULAÇÃO COM ARRAY 


array = ["Banana","Diego","30","3.54"]
for a in range(0,4):
    print("Tipo:" , type(array[a])) 
    print("Tem espaço?" , array[a].isspace())
    print("É um número?" , array[a].isnumeric()) 
    print("É alfabético" , array[a].isalpha()) 
    print("É alfanumérico" , array[a].isalnum()) 
    print("Está em maiuscula" , array[a].isupper()) 
    print("Está em minuscula" , array[a].islower()) 
    print("Está capitalizada?" , array[a].capitalize())

'''