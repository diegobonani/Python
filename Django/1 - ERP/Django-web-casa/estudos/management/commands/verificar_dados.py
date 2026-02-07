from django.core.management.base import BaseCommand
from usuarios.models import Perfil
from estudos.models import Matricula, DiarioBordo

class Command(BaseCommand):
    help = 'Diagnóstico completo dos dados escolares'

    def handle(self, *args, **kwargs):
        self.stdout.write("=== INICIANDO DIAGNÓSTICO DO BANCO DE DADOS ===\n")

        # 1. Verificar Alunos
        alunos = Perfil.objects.filter(esta_estudando=True)
        self.stdout.write(f"1. Total de Alunos 'Estudando': {alunos.count()}")
        
        for aluno in alunos:
            self.stdout.write(f"\n   [ALUNO] {aluno.nome_completo} (ID: {aluno.id})")
            
            # 2. Verificar Matrículas desse aluno
            matriculas = Matricula.objects.filter(aluno=aluno)
            if not matriculas.exists():
                self.stdout.write("      -> Nenhuma matrícula encontrada.")
                continue

            for mat in matriculas:
                tipo_ano = type(mat.ano_letivo)
                self.stdout.write(f"      -> Matrícula Ano: {mat.ano_letivo} (Tipo: {tipo_ano})")
                
                # 3. Verificar Notas (Diário de Bordo)
                diarios = DiarioBordo.objects.filter(matricula=mat)
                qtd_notas = diarios.count()
                self.stdout.write(f"         -> Quantidade de Notas/Matérias: {qtd_notas}")
                
                if qtd_notas > 0:
                    exemplo = diarios.first()
                    self.stdout.write(f"         -> Exemplo: {exemplo.disciplina_base.nome} = Nota 1º Bim: {exemplo.nota_1_bim}")
                else:
                    self.stdout.write("         -> [ALERTA] Matrícula existe mas NÃO TEM NOTAS.")

        self.stdout.write("\n=== FIM DO DIAGNÓSTICO ===")