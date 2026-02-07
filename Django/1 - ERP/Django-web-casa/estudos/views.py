import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count, Q 
from django.http import JsonResponse 
from django.template.loader import render_to_string 

from usuarios.models import Perfil
from .models import (
    Disciplina, AtividadeEstudo, TopicoConteudo, Avaliacao,
    Matricula, DiarioBordo, GradeCurricular,
    ModuloCurso, Aula, ProgressoAula
)
from .forms import DisciplinaForm, AtividadeEstudoForm, TopicoConteudoForm, AvaliacaoForm
from .utils import get_status_escolar_atual 
from .utils_questoes import gerar_questoes_por_topico 

# =====================================================================
# DASHBOARD E VISÃO GERAL
# =====================================================================

@login_required
def visao_geral_familia(request):
    if request.user.is_superuser:
        filhos = Perfil.objects.filter(esta_estudando=True).exclude(usuario__username='admin')
    else:
        filhos = Perfil.objects.filter(responsavel=request.user, esta_estudando=True)
        if not filhos.exists():
             filhos = Perfil.objects.filter(usuario=request.user, esta_estudando=True)

    dados_filhos = []
    for filho in filhos:
        atividades_hoje = AtividadeEstudo.objects.filter(
            disciplina__usuario=filho.usuario,
            concluido=False,
            data_agendada__lte=timezone.now()
        ).order_by('data_agendada', 'hora_inicio')[:5]

        ano_atual = timezone.now().year
        dificuldades = DiarioBordo.objects.filter(
            matricula__aluno=filho,
            matricula__ano_letivo=ano_atual
        ).filter(
            Q(dificuldade_leitura=True) | Q(dificuldade_escrita=True)
        )

        dados_filhos.append({
            'perfil': filho,
            'atividades': atividades_hoje,
            'dificuldades': dificuldades[:3], 
            'qtd_atividades': atividades_hoje.count(),
        })

    context = {'dados_filhos': dados_filhos, 'hoje': timezone.now()}
    return render(request, 'estudos/visao_geral.html', context)


@login_required
def gerenciar_estudos(request):
    # 1. BUSCAR TODA A FAMÍLIA (Exceto Admin)
    if request.user.is_superuser:
        base_familia = Perfil.objects.exclude(usuario__username='admin')
    else:
        familia_direta = Perfil.objects.filter(responsavel=request.user) | Perfil.objects.filter(usuario=request.user)
        filhos = Perfil.objects.filter(responsavel=request.user)
        if filhos.exists():
            try:
                conjuge = Perfil.objects.filter(filhos__in=filhos).exclude(usuario=request.user)
                base_familia = (familia_direta | conjuge).distinct()
            except:
                base_familia = familia_direta.distinct()
        else:
            base_familia = familia_direta.distinct()

    # 2. DEFINIR QUEM É ATIVO NO SISTEMA
    pessoas_ativas = base_familia.filter(
        Q(esta_estudando=True) | Q(esta_fazendo_curso=True)
    ).order_by('nome_completo')

    # 3. APLICAR O FILTRO DOS CHECKBOXES
    ids_selecionados = request.GET.getlist('filhos')
    
    if not ids_selecionados:
        alunos_na_tela = Perfil.objects.none()
    else:
        alunos_na_tela = pessoas_ativas.filter(id__in=ids_selecionados)

    # 4. CONFIGURAÇÕES DE DATA
    status_temporal = get_status_escolar_atual()
    ano_atual_sistema = 2026
    try:
        ano_selecionado = int(request.GET.get('ano', ano_atual_sistema))
    except ValueError:
        ano_selecionado = ano_atual_sistema
        
    anos_banco = list(Matricula.objects.values_list('ano_letivo', flat=True).distinct())
    conjunto_anos = set(anos_banco)
    conjunto_anos.add(ano_atual_sistema)
    anos_disponiveis = sorted(list(conjunto_anos), reverse=True)

    # 5. MONTAR OS DADOS PARA EXIBIÇÃO
    atividades_unificadas = []
    dificuldades_unificadas = []
    dados_por_aluno = []
    
    if alunos_na_tela.exists():
        usuarios_ids = [aluno.usuario.id for aluno in alunos_na_tela if aluno.usuario]
        
        atividades_unificadas = AtividadeEstudo.objects.filter(
            disciplina__usuario__id__in=usuarios_ids,
            concluido=False
        ).select_related('disciplina', 'disciplina__usuario').order_by('data_agendada', 'hora_inicio')

        for aluno in alunos_na_tela:
            
            exibir_aba_escola = aluno.esta_estudando
            exibir_aba_cursos = aluno.esta_fazendo_curso

            # ESCOLA
            matricula = None
            boletim_escola = []
            
            if exibir_aba_escola:
                matricula = Matricula.objects.filter(aluno=aluno, ano_letivo=ano_selecionado).first()
                if matricula:
                    diarios = DiarioBordo.objects.filter(matricula=matricula).select_related('disciplina_base')
                    for diario in diarios:
                        grade = GradeCurricular.objects.filter(
                            disciplina=diario.disciplina_base,
                            ano_serie=matricula.ano_serie_atual, 
                            nivel=matricula.nivel_atual
                        ).first()
                        topicos = grade.topicos.all() if grade else []
                        
                        boletim_escola.append({
                            'disciplina': diario.disciplina_base,
                            'diario': diario,
                            'topicos': topicos
                        })
                        if diario.dificuldade_leitura or diario.dificuldade_escrita:
                            dificuldades_unificadas.append(diario)

            # CURSOS
            cursos_extras = []
            if exibir_aba_cursos:
                disciplinas_raw = Disciplina.objects.filter(
                    usuario=aluno.usuario
                ).exclude(categoria='ESCOLA')

                for disc in disciplinas_raw:
                    if disc.curso_catalogo:
                        total = Aula.objects.filter(modulo__curso=disc.curso_catalogo).count()
                        concluidas = ProgressoAula.objects.filter(
                            usuario=aluno.usuario, 
                            aula__modulo__curso=disc.curso_catalogo, 
                            concluido=True
                        ).count()
                        
                        aulas_curso = Aula.objects.filter(modulo__curso=disc.curso_catalogo).order_by('modulo__ordem', 'ordem')
                        ids_vistos = ProgressoAula.objects.filter(
                            usuario=aluno.usuario,
                            aula__modulo__curso=disc.curso_catalogo,
                            concluido=True
                        ).values_list('aula_id', flat=True)
                        proxima_aula = aulas_curso.exclude(id__in=ids_vistos).first()
                        if not proxima_aula:
                            proxima_aula = aulas_curso.first()
                        disc.id_proxima_aula = proxima_aula.id if proxima_aula else None
                    else:
                        total = disc.atividades.count()
                        concluidas = disc.atividades.filter(concluido=True).count()
                        disc.id_proxima_aula = None
                    
                    disc.total_aulas_real = total
                    disc.aulas_concluidas = concluidas
                    
                    if total > 0:
                        disc.porcentagem = int((concluidas / total) * 100)
                    else:
                        disc.porcentagem = 0
                    cursos_extras.append(disc)

            dados_por_aluno.append({
                'aluno': aluno,
                'matricula': matricula,
                'boletim_escola': boletim_escola,
                'cursos_extras': cursos_extras,
                'tem_dados_escola': exibir_aba_escola and bool(matricula),
                'tem_dados_extra': exibir_aba_cursos 
            })

    context = {
        'filhos': pessoas_ativas, 
        'ids_selecionados': ids_selecionados, 
        'ano_selecionado': ano_selecionado,
        'anos_disponiveis': anos_disponiveis,
        'status': status_temporal,
        'atividades': atividades_unificadas,
        'dificuldades': dificuldades_unificadas,
        'dados_por_aluno': dados_por_aluno, 
        'form_disciplina': DisciplinaForm(),
        'form_atividade': AtividadeEstudoForm(user=request.user),
        'form_topico': TopicoConteudoForm(),
        'form_avaliacao': AvaliacaoForm(),
    }
    
    return render(request, 'estudos/gerenciar_estudos.html', context)


# =====================================================================
# API PLAYER - ONDE A MÁGICA E O ERRO ACONTECEM
# =====================================================================

@login_required
def api_aula_player(request, aula_id):
    """
    Retorna os dados da aula. 
    Lógica de fallback e diagnóstico incluída.
    """
    aula_atual = get_object_or_404(Aula, id=aula_id)
    curso = aula_atual.modulo.curso
    usuario_alvo = request.user

    # POST (Marcar Concluído)
    if request.method == "POST":
        aluno_id = request.POST.get('aluno_id')
        if aluno_id:
            perfil = Perfil.objects.filter(id=aluno_id).first()
            if perfil: usuario_alvo = perfil.usuario
            
        ProgressoAula.objects.update_or_create(
            usuario=usuario_alvo,
            aula=aula_atual,
            defaults={'concluido': True}
        )
    
    elif request.method == "GET" and request.GET.get('aluno_id'):
        perfil = Perfil.objects.filter(id=request.GET.get('aluno_id')).first()
        if perfil: usuario_alvo = perfil.usuario

    # Navegação
    proxima = Aula.objects.filter(modulo=aula_atual.modulo, ordem__gt=aula_atual.ordem).order_by('ordem').first()
    if not proxima:
        prox_mod = ModuloCurso.objects.filter(curso=curso, ordem__gt=aula_atual.modulo.ordem).order_by('ordem').first()
        if prox_mod: proxima = prox_mod.aulas.order_by('ordem').first()

    anterior = Aula.objects.filter(modulo=aula_atual.modulo, ordem__lt=aula_atual.ordem).order_by('-ordem').first()
    if not anterior:
        ant_mod = ModuloCurso.objects.filter(curso=curso, ordem__lt=aula_atual.modulo.ordem).order_by('-ordem').first()
        if ant_mod: anterior = ant_mod.aulas.order_by('-ordem').first()

    # --- ÁREA DE DIAGNÓSTICO E GERAÇÃO DE LINK ---
    print(f"\n🎬 --- PLAY: {aula_atual.titulo} (ID {aula_atual.id}) ---")
    
    url_final = ""
    is_file = False
    usando_local = False

    # 1. TENTA LOCAL
    if aula_atual.video_arquivo:
        try:
            caminho_fisico = aula_atual.video_arquivo.path
            print(f"   📂 Verificando Disco: {caminho_fisico}")
            
            if os.path.exists(caminho_fisico):
                print("   ✅ Arquivo Existe! Usando Local.")
                url_final = aula_atual.video_arquivo.url
                is_file = True
                usando_local = True
            else:
                print("   ❌ Arquivo NÃO existe (Deletado ou Caminho Errado).")
        except Exception as e:
            print(f"   ⚠️ Erro ao checar disco: {e}")

    # 2. TENTA TELEGRAM (Se não achou local)
    if not usando_local:
        if aula_atual.video_link and "tg://" in aula_atual.video_link:
            print(f"   ☁️ Trocando para Telegram: {aula_atual.video_link}")
            try:
                link_limpo = aula_atual.video_link.replace("tg://", "")
                partes = link_limpo.split("/")
                channel_id = partes[0] 
                msg_id = partes[1]
                
                # Gera URL do Streamer
                url_final = f"http://127.0.0.1:8080/stream/{channel_id}/{msg_id}"
                is_file = True 
                print(f"   🚀 URL Gerada: {url_final}")
            except Exception as e:
                url_final = "#erro-link"
                print(f"   ❌ Erro ao gerar link: {e}")
        else:
            print("   ⚠️ Sem link do Telegram no Banco de Dados!")

    # 3. YOUTUBE/VIMEO
    elif not usando_local and aula_atual.video_link and "http" in aula_atual.video_link:
        url_final = aula_atual.video_link
        is_file = False

    if url_final == "":
        print("   ⛔ NENHUMA URL ENCONTRADA. O VÍDEO VAI TRAVAR.")

    # Sidebar
    estrutura_curso = []
    modulos = ModuloCurso.objects.filter(curso=curso).order_by('ordem')
    for mod in modulos:
        aulas_do_modulo = mod.aulas.all().order_by('ordem')
        if aulas_do_modulo.exists():
            aulas_mod = []
            for aula in aulas_do_modulo:
                visto = ProgressoAula.objects.filter(usuario=usuario_alvo, aula=aula, concluido=True).exists()
                aulas_mod.append({'aula': aula, 'visto': visto})
            estrutura_curso.append({'modulo': mod, 'aulas': aulas_mod})

    html_playlist = render_to_string('estudos/components/playlist_sidebar.html', {
        'estrutura': estrutura_curso,
        'aula_atual': aula_atual
    })

    data = {
        'id': aula_atual.id,
        'titulo': aula_atual.titulo,
        'modulo': aula_atual.modulo.titulo,
        'video_url': url_final, 
        'is_file': is_file, 
        'proxima_id': proxima.id if proxima else None,
        'anterior_id': anterior.id if anterior else None,
        'playlist_html': html_playlist 
    }
    
    return JsonResponse(data)


# ... (Resto do arquivo - CRUDs - continua igual) ...
@login_required
@require_POST
def registrar_estudo_grupo(request):
    ids_participantes = request.POST.getlist('participantes')
    nome_materia = request.POST.get('materia_nome')
    conteudo_estudado = request.POST.get('conteudo')

    if not ids_participantes or not nome_materia:
        messages.error(request, "Selecione os participantes e a matéria.")
        return redirect('estudos:gerenciar_estudos')

    count_sucesso = 0
    count_duplicados = 0

    for perfil_id in ids_participantes:
        perfil = Perfil.objects.filter(id=perfil_id).first()
        if not perfil: continue

        disciplina, created = Disciplina.objects.get_or_create(
            usuario=perfil.usuario,
            nome__iexact=nome_materia,
            defaults={'nome': nome_materia, 'categoria': 'EXTRA'}
        )

        ja_existe = AtividadeEstudo.objects.filter(
            disciplina=disciplina, 
            titulo__iexact=conteudo_estudado
        ).exists()

        if ja_existe:
            count_duplicados += 1
            continue

        AtividadeEstudo.objects.create(
            disciplina=disciplina,
            titulo=conteudo_estudado,
            data_agendada=timezone.now().date(),
            hora_inicio=timezone.now().time(),
            concluido=True
        )
        count_sucesso += 1

    if count_sucesso > 0:
        messages.success(request, f"Aula registrada para {count_sucesso} pessoas! 🚀")
    
    if count_duplicados > 0:
        messages.warning(request, f"{count_duplicados} registros ignorados pois a aula já existia.")

    return redirect(request.META.get('HTTP_REFERER') or 'estudos:gerenciar_estudos')

@login_required
def adicionar_disciplina(request):
    if request.method == 'POST':
        aluno_id = request.POST.get('aluno_id')
        categoria = request.POST.get('categoria', 'EXTRA') 
        nome_curso = request.POST.get('nome')

        if Disciplina.objects.filter(usuario_id=aluno_id, nome__iexact=nome_curso).exists():
            messages.error(request, f"Erro: Este aluno já possui um curso chamado '{nome_curso}'.")
            return redirect(request.META.get('HTTP_REFERER') or 'estudos:gerenciar_estudos')

        form = DisciplinaForm(request.POST)
        if form.is_valid() and aluno_id:
            disciplina = form.save(commit=False)
            disciplina.usuario_id = aluno_id 
            disciplina.categoria = categoria 
            disciplina.save()
            messages.success(request, "Disciplina criada manualmente!")
            
    return redirect(request.META.get('HTTP_REFERER') or 'estudos:gerenciar_estudos')

@login_required
def editar_disciplina(request, disciplina_id):
    disciplina = get_object_or_404(Disciplina, id=disciplina_id)
    
    if request.method == 'POST':
        novo_nome = request.POST.get('novo_nome')
        nova_categoria = request.POST.get('nova_categoria')
        
        duplicado = Disciplina.objects.filter(
            usuario=disciplina.usuario, 
            nome__iexact=novo_nome
        ).exclude(id=disciplina.id).exists()
        
        if duplicado:
            messages.error(request, f"Já existe outro curso com o nome '{novo_nome}'.")
        else:
            disciplina.nome = novo_nome
            disciplina.categoria = nova_categoria
            disciplina.save()
            messages.success(request, "Curso atualizado com sucesso!")
            
    return redirect('estudos:gerenciar_estudos')

@login_required
def excluir_disciplina(request, disciplina_id):
    disciplina = get_object_or_404(Disciplina, id=disciplina_id)
    nome_bkp = disciplina.nome
    disciplina.delete()
    messages.success(request, f"O curso '{nome_bkp}' e todo o histórico foram removidos.")
    return redirect('estudos:gerenciar_estudos')

@require_POST
def salvar_notas(request):
    referer = request.META.get('HTTP_REFERER')
    for key, value in request.POST.items():
        try:
            if not '_' in key: continue
            prefixo, diario_id = key.split('_') 
            diario = DiarioBordo.objects.filter(id=diario_id).first()
            if not diario: continue

            val_tratado = float(value.replace(',', '.')) if value.strip() != '' else None

            if prefixo == 'n1': diario.nota_1_bim = val_tratado
            elif prefixo == 'n2': diario.nota_2_bim = val_tratado
            elif prefixo == 'n3': diario.nota_3_bim = val_tratado
            elif prefixo == 'n4': diario.nota_4_bim = val_tratado
            elif prefixo == 'f': diario.total_faltas = int(val_tratado) if val_tratado is not None else 0

            diario.save()
        except ValueError:
            continue 

    messages.success(request, "Boletim atualizado com sucesso!")
    return redirect(referer if referer else 'estudos:gerenciar_estudos')

@login_required
def adicionar_atividade(request):
    if request.method == 'POST':
        form = AtividadeEstudoForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Tarefa agendada!")
    return redirect(request.META.get('HTTP_REFERER') or 'estudos:gerenciar_estudos')

@login_required
def adicionar_dificuldade(request):
    if request.method == 'POST':
        form = TopicoConteudoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Dificuldade registrada.")
    return redirect(request.META.get('HTTP_REFERER') or 'estudos:gerenciar_estudos')

@login_required
def adicionar_avaliacao(request):
    if request.method == 'POST':
        form = AvaliacaoForm(request.POST)
        if form.is_valid():
            avaliacao = form.save(commit=False)
            PONTOS_POR_PROVA = 50 
            NOTA_CORTE = 7.0
            if avaliacao.nota_obtida and avaliacao.nota_obtida >= NOTA_CORTE:
                aluno_perfil = avaliacao.disciplina.usuario.perfil
                aluno_perfil.saldo_pontos += PONTOS_POR_PROVA
                aluno_perfil.save()
                messages.success(request, f"Nota lançada! {aluno_perfil.nome_completo} ganhou +{PONTOS_POR_PROVA} XP por mérito! 🤑")
            else:
                messages.success(request, "Nota lançada.")
            avaliacao.save()
    return redirect(request.META.get('HTTP_REFERER') or 'estudos:gerenciar_estudos')

@login_required
def assistir_curso(request, disciplina_id, aula_id=None):
    return redirect('estudos:gerenciar_estudos')

@login_required
def api_gerar_questoes(request):
    titulo = request.GET.get('titulo', '')
    questoes = gerar_questoes_por_topico(titulo)
    return JsonResponse({'questoes': questoes})