$(document).ready(function() {
    // As URLs são passadas pelo template HTML principal (gerenciar_lavanderia.html)
    
    const ciclosContainer = $('#ciclos-container');
    const historicoContainer = $('#historico-container');
    
    let modalEditarCesto;
    let modalIniciarCiclo;
    let modalConfirmar;
    let modalAdicionarCesto;

    function recarregarPainelCiclos() {
        // Usa a variável global
        ciclosContainer.load(window.URL_ABA_CICLOS, function() {
            // Inicializa as instâncias dos modais APÓS o HTML ser carregado
            modalAdicionarCesto = new bootstrap.Modal(document.getElementById('modalAdicionarCesto'));
            modalEditarCesto = new bootstrap.Modal(document.getElementById('modalEditarCesto'));
            modalIniciarCiclo = new bootstrap.Modal(document.getElementById('modalIniciarCiclo'));
            if (!modalConfirmar) {
                modalConfirmar = new bootstrap.Modal(document.getElementById('modalConfirmarExclusao'));
            }
        });
    }

    // Carrega a primeira aba (Painel de Controle) imediatamente
    if (ciclosContainer.length) {
        recarregarPainelCiclos();
    }

    // Carrega a aba de Histórico apenas na primeira vez que ela for clicada
    $('button[data-bs-toggle="tab"][id="historico-tab"]').one('shown.bs.tab', function (e) {
        historicoContainer.load(window.URL_ABA_HISTORICO); // Usa a variável global
    });

    // --- LÓGICA DO FILTRO DE HISTÓRICO ---
    $(document).on('submit', '#form-filtro-historico', function(e) {
        e.preventDefault();
        const data = $(this).serialize();
        historicoContainer.html('<div class="d-flex justify-content-center p-5"><div class="spinner-border" role="status"></div></div>');
        historicoContainer.load(`${window.URL_ABA_HISTORICO}?${data}`); // Usa a variável global
    });
    $(document).on('click', '.btn-periodo', function() {
        const periodo = $(this).data('periodo');
        const hoje = new Date();
        const dataFim = hoje.toISOString().split('T')[0];
        let dataInicio;
        if (periodo === 'hoje') { dataInicio = dataFim; } 
        else if (periodo === 'semana') { let d = new Date(); d.setDate(hoje.getDate() - 6); dataInicio = d.toISOString().split('T')[0]; } 
        else if (periodo === 'mes') { dataInicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1).toISOString().split('T')[0]; }
        $('#data_inicio').val(dataInicio);
        $('#data_fim').val(dataFim);
        $('#form-filtro-historico').submit();
    });
    $('button[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
        setTimeout(function() { $($.fn.dataTable.tables(true)).DataTable().columns.adjust(); }, 200);
    });

    // --- LÓGICA DO PAINEL DE CONTROLE (ABA CICLOS) ---

    // Adicionar Cesto
    $(document).on('submit', '#formAdicionarCesto', function(e) {
        e.preventDefault();
        var form = $(this);
        $.ajax({
            type: 'POST', url: form.attr('action'), data: form.serialize(),
            success: function(response) {
                ciclosContainer.html(response); // Recarrega o painel com o novo HTML
            },
            error: function() { alert('Erro ao adicionar o cesto.'); }
        });
    });

    // --- LÓGICA DE EDITAR CESTO ---
    $(document).on('click', '.btn-editar-cesto', function() {
        var cestoId = $(this).data('id');
        var form = $('#formEditarCesto');
        
        // CORREÇÃO: Usa as variáveis globais do window
        form.attr('action', window.URL_CESTO_EDITAR.replace('0', cestoId));
        form.find('#form-errors-editar-cesto').hide().empty();

        $.ajax({
            url: window.URL_CESTO_JSON.replace('0', cestoId),
            success: function(data) {
                form.find('#id_usuario').val(data.usuario);
                form.find('#id_tipo_roupa').val(data.tipo_roupa);
                form.find('#id_quantidade_cestos').val(data.quantidade_cestos);
                form.find('#id_prioridade').prop('checked', data.prioridade);
            }
        });
    });

    $(document).on('submit', '#formEditarCesto', function(e) {
        e.preventDefault();
        var form = $(this);
        $.ajax({
            type: 'POST', url: form.attr('action'), data: form.serialize(),
            success: function(response) {
                if(response.success) {
                    modalEditarCesto.hide();
                    recarregarPainelCiclos(); 
                }
            },
            error: function(xhr) {
                var response = xhr.responseJSON;
                var errorDiv = form.find('#form-errors-editar-cesto');
                var errorMessage = 'Ocorreu um erro.';
                if (response && response.errors) {
                    errorMessage = '';
                    var errors = JSON.parse(response.errors);
                    for (var field in errors) { errorMessage += `<p class="mb-1">${field}: ${errors[field][0].message}</p>`; }
                }
                errorDiv.html(errorMessage).show();
            }
        });
    });

    // --- LÓGICA DE EXCLUIR CESTO ---
    $(document).on('click', '.btn-excluir-cesto', function() {
        var cestoId = $(this).data('id');
        if (!modalConfirmar) {
             modalConfirmar = new bootstrap.Modal(document.getElementById('modalConfirmarExclusao'));
        }
        
        $('#modalConfirmarLabel').text('Confirmar Exclusão');
        $('#modalConfirmarTexto').text('Tem certeza que deseja excluir este cesto de roupas?');
        // CORREÇÃO: Usa a variável global
        $('#formConfirmacao').attr('action', window.URL_CESTO_EXCLUIR.replace('0', cestoId));
        modalConfirmar.show();
    });

    // Intercepta a submissão do formulário de confirmação
    $('#formConfirmacao').on('submit', function(e) {
        var form = $(this);
        var url = form.attr('action');

        // Apenas intercepta se for uma URL de lavanderia
        if (url.includes('/lavanderia/')) {
            e.preventDefault(); 
            $.ajax({
                type: 'POST', url: url, data: form.serialize(),
                success: function(response) {
                    $('#modalConfirmarExclusao').modal('hide');
                    if (response.success) {
                        recarregarPainelCiclos(); 
                    } else {
                        alert('Erro ao excluir: ' + response.message);
                    }
                },
                error: function() { alert('Erro de conexão ao tentar excluir.'); }
            });
        }
        // Se for outra URL (ex: /estoque/...), deixa o submit padrão continuar
    });

    // --- LÓGICA DE INICIAR CICLO ---
    $(document).on('click', '.btn-iniciar-ciclo', function (event) {
        var button = $(this);
        var tipoCarga = button.data('tipo-carga');
        var modal = $('#modalIniciarCiclo');
        modal.find('#input-tipo-carga').val(tipoCarga);
    });

    $(document).on('submit', '#formIniciarCiclo', function(e) {
        e.preventDefault();
        var form = $(this);
        $.ajax({
            type: 'POST', url: form.attr('action'), data: form.serialize(),
            success: function(response) {
                if (response.success) {
                    $('#modalIniciarCiclo').modal('hide');
                    recarregarPainelCiclos();
                } else {
                    alert('Erro ao iniciar ciclo: ' + response.message);
                }
            },
            error: function() { alert('Erro de conexão ao tentar iniciar ciclo.'); }
        });
    });

    // --- LÓGICA DE AVANÇAR ETAPA DO CICLO ---
    $(document).on('click', '.btn-avancar-etapa', function() {
        var button = $(this);
        var cicloId = button.data('ciclo-id');
        var novoStatus = button.data('novo-status');
        
        // Tenta pegar o token do form de adicionar cesto, se ele existir
        var csrfToken = $('#formAdicionarCesto [name=csrfmiddlewaretoken]').val();
        if (!csrfToken) {
            // Fallback para o token principal da página
            csrfToken = $('[name=csrfmiddlewaretoken]').val();
        }

        $.ajax({
            type: 'POST',
            // CORREÇÃO: Usa a variável global
            url: window.URL_AVANCAR_ETAPA.replace('0', cicloId),
            data: {
                'novo_status': novoStatus,
                'csrfmiddlewaretoken': csrfToken
            },
            success: function(response) {
                if (response.success) {
                    recarregarPainelCiclos(); 
                }
            },
            error: function() {
                alert('Erro ao avançar etapa.');
            }
        });
    });

    // --- LÓGICA DE ADICIONAR/REMOVER PRODUTO ---
    $(document).on('submit', 'form[id^="formAdicionarProdutoCiclo-"]', function(e) {
        e.preventDefault();
        var form = $(this);
        $.ajax({
            type: 'POST', url: form.attr('action'), data: form.serialize(),
            success: function(response) {
                if(response.success) { recarregarPainelCiclos(); }
            },
            error: function(xhr) {
                var response = xhr.responseJSON;
                alert('Erro ao adicionar produto: ' + response.message);
            }
        });
    });

    $(document).on('click', '.btn-remover-produto', function() {
        var consumoId = $(this).data('consumo-id');
        
        var csrfToken = $('#formAdicionarCesto [name=csrfmiddlewaretoken]').val();
        if (!csrfToken) {
            csrfToken = $('[name=csrfmiddlewaretoken]').val();
        }

        $.ajax({
            type: 'POST',
            // CORREÇÃO: Usa a variável global
            url: window.URL_REMOVER_PRODUTO.replace('0', consumoId),
            data: { 'csrfmiddlewaretoken': csrfToken },
            success: function(response) {
                if(response.success) { recarregarPainelCiclos(); }
            },
            error: function() { alert('Erro ao remover produto.'); }
        });
    });
});