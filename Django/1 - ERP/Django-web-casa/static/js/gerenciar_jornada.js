// Em: static/js/gerenciar_jornada.js

$(document).ready(function() {
    // === INICIALIZA TODOS OS MODAIS ===
    // Modais de Jornada
    const modalAdicionarPontoAdmin = new bootstrap.Modal(document.getElementById('modalAdicionarPontoAdmin'));
    const modalEditarPontoAdmin = new bootstrap.Modal(document.getElementById('modalEditarPontoAdmin'));
    const modalExcluirJornadaAdmin = new bootstrap.Modal(document.getElementById('modalExcluirJornadaAdmin'));
    
    // Modais de Balanço (Novos)
    const modalAdicionarBalancoAdmin = new bootstrap.Modal(document.getElementById('modalAdicionarBalancoAdmin'));
    const modalEditarBalancoAdmin = new bootstrap.Modal(document.getElementById('modalEditarBalancoAdmin'));
    const modalExcluirBalancoAdmin = new bootstrap.Modal(document.getElementById('modalExcluirBalancoAdmin'));

    // =================================================================
    // 0. LÓGICA DO FILTRO DE DATA DINÂMICO
    // =================================================================
    function setupFiltrosDeData() {
        const filtroTipo = $('#filtro-tipo');
        const filtroDia = $('#filtro-dia-container');
        const filtroMes = $('#filtro-mes-container');
        const filtroPeriodo = $('#filtro-periodo-container');

        function toggleFiltros() {
            const tipo = filtroTipo.val();
            // Esconde todos primeiro
            filtroDia.hide();
            filtroMes.hide();
            filtroPeriodo.hide();
            
            // Mostra o correto
            if (tipo === 'dia') {
                filtroDia.show();
            } else if (tipo === 'mes') {
                filtroMes.show();
            } else if (tipo === 'periodo') {
                filtroPeriodo.show();
            }
        }

        // Adiciona o gatilho para o dropdown 'Tipo de Filtro'.
        filtroTipo.on('change', function() {
            toggleFiltros();
        });
        
        // Roda na inicialização para mostrar o filtro correto
        toggleFiltros();
    }
    setupFiltrosDeData();

    // =================================================================
    // 1. CÁLCULO DINÂMICO DE HORAS (para Linha Rápida de JORNADA)
    // =================================================================
    function calcularHorasLinhaRapida() {
        const linha = $('#linha-insercao-rapida-admin');
        if (!linha.length) return; 

        const entrada = linha.find('#quick-entrada-admin').val();
        const saidaAlmoco = linha.find('#quick-saida-almoco-admin').val();
        const retornoAlmoco = linha.find('#quick-retorno-almoco-admin').val();
        const saida = linha.find('#quick-saida-admin').val();
        const tipoDia = linha.find('#quick-tipo-dia-admin').val();

        const tdAlmoco = linha.find('.quick-total-almoco');
        const tdTrabalhado = linha.find('.quick-total-trabalhado');
        const tdExtras = linha.find('.quick-total-extras');
        
        function parseTempo(timeStr) {
            if (!timeStr) return 0;
            const parts = timeStr.split(':');
            if (parts.length !== 2) return 0;
            const h = parseInt(parts[0], 10), m = parseInt(parts[1], 10);
            if (isNaN(h) || isNaN(m)) return 0;
            return h * 60 + m;
        }

        const minEntrada = parseTempo(entrada), minSaidaAlmoco = parseTempo(saidaAlmoco);
        const minRetornoAlmoco = parseTempo(retornoAlmoco), minSaida = parseTempo(saida);
        let minTrabalhadosManha = 0, minTrabalhadosTarde = 0, minAlmoco = 0;

        if (tipoDia === 'NORMAL') {
            if (minEntrada && minSaidaAlmoco && minSaidaAlmoco > minEntrada) { minTrabalhadosManha = minSaidaAlmoco - minEntrada; }
            if (minRetornoAlmoco && minSaida && minSaida > minRetornoAlmoco) { minTrabalhadosTarde = minSaida - minRetornoAlmoco; }
            if (minSaidaAlmoco && minRetornoAlmoco && minRetornoAlmoco > minSaidaAlmoco) { minAlmoco = minRetornoAlmoco - minSaidaAlmoco; }
        } else if (tipoDia !== 'FOLGA' && tipoDia !== 'ATESTADO') {
            if (minEntrada && minSaida && minSaida > minEntrada) { minTrabalhadosManha = minSaida - minEntrada; }
        }
        
        const totalMinTrabalhados = minTrabalhadosManha + minTrabalhadosTarde;
        let jornadaPadraoMin = 480; 
        if (tipoDia === 'SABADO') jornadaPadraoMin = 240; 
        if (['FERIADO', 'PLANTAO', 'FOLGA', 'ATESTADO'].includes(tipoDia)) {
            jornadaPadraoMin = 0;
        }
        
        const totalMinExtras = Math.max(0, totalMinTrabalhados - jornadaPadraoMin);
        
        tdAlmoco.text((minAlmoco / 60).toFixed(2) + 'h');
        tdTrabalhado.text((totalMinTrabalhados / 60).toFixed(2) + 'h');
        
        if (totalMinExtras > 0) {
            tdExtras.html(`<span class="badge bg-warning text-dark">+${(totalMinExtras / 60).toFixed(2)}h</span>`);
        } else {
            tdExtras.html('<span class="text-muted">-</span>');
        }
    }

    // Gatilho para a Linha Rápida (Jornada)
    $('#tabelaGerenciarJornada').on('change', '#quick-tipo-dia-admin', function() {
        const linha = $(this).closest('tr');
        const tipoDia = $(this).val();
        const almocoInputs = linha.find('#quick-saida-almoco-admin, #quick-retorno-almoco-admin');
        const horaInputs = linha.find('#quick-entrada-admin, #quick-saida-admin');

        if (tipoDia === 'NORMAL') {
            almocoInputs.prop('disabled', false);
            horaInputs.prop('disabled', false);
        } else if (tipoDia === 'FOLGA' || tipoDia === 'ATESTADO') {
            almocoInputs.prop('disabled', true).val('');
            horaInputs.prop('disabled', true).val('');
        } else { // Sábado, Feriado, Plantão
            almocoInputs.prop('disabled', true).val('');
            horaInputs.prop('disabled', false);
        }
        calcularHorasLinhaRapida(); 
    });
    $('#tabelaGerenciarJornada').on('input change', '.quick-input-admin', function() {
        calcularHorasLinhaRapida();
    });

    // =================================================================
    // 2. GESTOR: ADICIONAR REGISTRO (JORNADA)
    // =================================================================
    $('#formAdicionarPontoAdmin').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        $.ajax({
            type: 'POST', 
            url: window.URL_ADMIN_ADD_PONTO, 
            data: form.serialize(),
            success: function(response) {
                if (response.success) {
                    modalAdicionarPontoAdmin.hide();
                    recarregarComCacheBuster(); // Força recarregamento
                }
            },
            error: function(xhr) {
                const errorDiv = form.find('#form-errors-add-jornada');
                let msg = 'Erro ao salvar. Verifique se já não existe um registro deste tipo para este dia.';
                errorDiv.html(msg).show();
            }
        });
    });

    // =================================================================
    // 3. GESTOR: INSERÇÃO RÁPIDA (JORNADA)
    // =================================================================
    $('#btn-salvar-rapido-jornada').on('click', function() {
        const btn = $(this);
        const linha = $('#linha-insercao-rapida-admin');
        const data = {
            'csrfmiddlewaretoken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            'usuario': linha.find('#quick-usuario-admin').val(),
            'data': window.DATA_FILTRO_ATUAL, 
            'tipo_dia': linha.find('#quick-tipo-dia-admin').val(),
            'entrada': linha.find('#quick-entrada-admin').val(),
            'saida_almoco': linha.find('#quick-saida-almoco-admin').val(),
            'retorno_almoco': linha.find('#quick-retorno-almoco-admin').val(),
            'saida': linha.find('#quick-saida-admin').val()
        };
        if (!data.usuario) { alert('Erro: Colaborador não selecionado.'); return; }
        btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i>');
        
        $.ajax({
            type: 'POST', url: window.URL_ADMIN_ADD_PONTO, data: data,
            success: function(response) { recarregarComCacheBuster(); },
            error: function(xhr) { 
                alert('Erro ao salvar. Verifique se já não existe um registro deste tipo para este dia.');
                btn.prop('disabled', false).html('<i class="fas fa-check"></i>');
            }
        });
    });

    // =================================================================
    // 4. GESTOR: LÓGICA DE EDIÇÃO (JORNADA)
    // =================================================================
    
    // Clicou no botão de editar (lápis) - ABRE O MODAL
    $('#tabelaGerenciarJornada').on('click', '.btn-editar-jornada', function() {
        const pk = $(this).data('id');
        const form = $('#formEditarPontoAdmin');
        const modalBody = form.find('.modal-body');
        
        form.attr('action', window.URL_ADMIN_EDITAR_PONTO.replace('0', pk));
        modalBody.html('<p class="text-center"><i class="fas fa-spinner fa-spin"></i> Carregando...</p>');

        $.ajax({
            type: 'GET',
            url: window.URL_ADMIN_GET_PONTO.replace('0', pk),
            success: function(data) {
                let formHtml = window.FORM_JORNADA_HTML
                    .replace(/<p>/g, '<div class="mb-3">').replace(/<\/p>/g, '</div>');
                
                let $tempHtml = $('<div>').html(formHtml);
                $tempHtml.find('label[for="id_usuario"]').closest('div.mb-3').remove();
                
                modalBody.html($tempHtml.html());
                
                // Preenche os dados
                form.find('[name="data"]').val(data.data);
                form.find('[name="tipo_dia"]').val(data.tipo_dia);
                form.find('[name="entrada"]').val(data.entrada);
                form.find('[name="saida_almoco"]').val(data.saida_almoco);
                form.find('[name="retorno_almoco"]').val(data.retorno_almoco);
                form.find('[name="saida"]').val(data.saida);
                form.find('[name="atestado_cid"]').val(data.atestado_cid || '');
                form.find('[name="atestado_crm"]').val(data.atestado_crm || '');
                form.find('[name="atestado_obs"]').val(data.atestado_obs || '');

                $('#modalEditarPontoAdmin .modal-title').html(`<i class="fas fa-user-edit me-2"></i>Editar Jornada de <strong>${data.usuario_nome}</strong>`);
                
                // CHAMA A LÓGICA INTELIGENTE DO MODAL
                form.find('[name="data"]').trigger('change'); 
            },
            error: function() {
                modalBody.html('<p class="text-danger">Erro ao carregar dados.</p>');
            }
        });
    });

    // Clicou em Salvar (no Modal de Edição de JORNADA)
    $('#formEditarPontoAdmin').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        const btnSave = form.find('[type="submit"]');
        btnSave.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Salvando...');

        $.ajax({
            type: 'POST',
            url: form.attr('action'),
            data: form.serialize(),
            success: function(response) {
                if (response.success) { 
                    modalEditarAdmin.hide();
                    recarregarComCacheBuster();
                }
            },
            error: function(xhr) {
                alert('Erro ao salvar. Verifique os dados.');
                btnSave.prop('disabled', false).html('Salvar Alterações');
            }
        });
    });

    // =================================================================
    // 5. GESTOR: EXCLUIR REGISTRO (JORNADA)
    // =================================================================
    $('#tabelaGerenciarJornada').on('click', '.btn-excluir-jornada', function() {
        const pk = $(this).data('id');
        $('#formExcluirJornadaAdmin').attr('action', window.URL_ADMIN_DELETAR_PONTO.replace('0', pk));
    });

    $('#formExcluirJornadaAdmin').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        $.ajax({
            type: 'POST',
            url: form.attr('action'),
            data: form.serialize(),
            success: function(response) {
                if (response.success) {
                    modalExcluirJornadaAdmin.hide();
                    recarregarComCacheBuster();
                }
            },
            error: function() { alert('Erro ao excluir.'); }
        });
    });

    // =================================================================
    // 6. LÓGICA INTELIGENTE (MODAL JORNADA) - Mostrar/Esconder campos
    // =================================================================
    function toggleModalFieldsJornada(form) {
        const tipoDia = form.find('[name="tipo_dia"]');
        
        // Seletor universal para <p> (do as_p) e <div> (do form de edição)
        const containerSelector = 'p, .mb-3'; 
        
        const camposHorario_divs = form.find('[name="entrada"], [name="saida_almoco"], [name="retorno_almoco"], [name="saida"]').closest(containerSelector);
        const camposAlmoco_divs = form.find('[name="saida_almoco"], [name="retorno_almoco"]').closest(containerSelector);
        const camposAtestado_divs = form.find('[name="atestado_cid"], [name="atestado_crm"], [name="atestado_obs"]').closest(containerSelector);

        // Esconde todos os campos opcionais primeiro
        camposHorario_divs.hide();
        camposAtestado_divs.hide();

        if (tipoDia.val() === 'ATESTADO') {
            camposAtestado_divs.show();
            camposHorario_divs.find('input[type="time"]').val('');
        } else if (tipoDia.val() === 'FOLGA') {
            camposHorario_divs.find('input[type="time"]').val('');
            camposAtestado_divs.find('input, textarea').val('');
        } else {
            // NORMAL, SÁBADO, FERIADO, PLANTÃO
            camposAtestado_divs.find('input, textarea').val('');
            camposHorario_divs.show();

            if (tipoDia.val() !== 'NORMAL') {
                camposAlmoco_divs.hide();
                camposAlmoco_divs.find('input').val('');
            } else {
                camposAlmoco_divs.show();
            }
        }
    }

    // =================================================================
    // 7. LÓGICA INTELIGENTE (MODAL JORNADA) - MUDANÇA DE DATA
    // =================================================================
    function setupModalDateTriggersJornada() {
        function onDateChange(event) {
            const form = $(this).closest('form');
            const dateString = $(this).val();
            if (!dateString) return; 

            const data = new Date(dateString + 'T12:00:00');
            const dayOfWeek = data.getUTCDay(); // 0=Dom, 6=Sáb
            
            const tipoDiaSelect = form.find('[name="tipo_dia"]');
            const currentTipoDia = tipoDiaSelect.val();

            tipoDiaSelect.find('option').show();
            
            if (dayOfWeek === 6) { // Sábado
                tipoDiaSelect.find('option[value="NORMAL"], option[value="FOLGA"], option[value="PLANTAO"]').hide();
                if (!['SABADO', 'FERIADO', 'ATESTADO'].includes(currentTipoDia)) {
                    tipoDiaSelect.val('SABADO');
                }
            } 
            else if (dayOfWeek === 0) { // Domingo
                tipoDiaSelect.find('option[value="NORMAL"], option[value="SABADO"]').hide();
                if (!['FERIADO', 'PLANTAO', 'FOLGA', 'ATESTADO'].includes(currentTipoDia)) {
                    tipoDiaSelect.val('FOLGA'); 
                }
            } 
            else { // Dia de Semana
                tipoDiaSelect.find('option[value="SABADO"], option[value="FOLGA"], option[value="PLANTAO"]').hide();
                if (!['NORMAL', 'FERIADO', 'ATESTADO'].includes(currentTipoDia)) {
                     tipoDiaSelect.val('NORMAL');
                }
            }
            toggleModalFieldsJornada(form); 
        }

        $('body').on('change', '#modalAdicionarPontoAdmin [name="data"]', onDateChange);
        $('body').on('change', '#modalEditarPontoAdmin [name="data"]', onDateChange);
        
        $('#modalAdicionarPontoAdmin').on('shown.bs.modal', function () {
            const dataInput = $(this).find('[name="data"]');
            if (!dataInput.val()) {
                const hoje = new Date().toISOString().split('T')[0];
                dataInput.val(hoje);
            }
            $(this).find('[name="data"]').trigger('change');
        });
    }
    setupModalDateTriggersJornada(); 

    $('body').on('change', '#modalAdicionarPontoAdmin [name="tipo_dia"], #modalEditarPontoAdmin [name="tipo_dia"]', function() {
        const form = $(this).closest('form');
        toggleModalFieldsJornada(form);
    });


    // =================================================================
    // 8. GESTOR: ADICIONAR REGISTRO (BALANÇO) - NOVO
    // =================================================================
    $('#formAdicionarBalancoAdmin').on('submit', function(e) {
        e.preventDefault();
        const form = $(this)[0]; // Pega o elemento do formulário
        const formData = new FormData(form); // Usa FormData para upload de arquivo
        const errorDiv = $(form).find('#form-errors-add-balanco');
        errorDiv.hide().empty();

        $.ajax({
            type: 'POST', 
            url: window.URL_ADMIN_ADD_BALANCO, 
            data: formData,
            processData: false, // Necessário para FormData
            contentType: false, // Necessário para FormData
            success: function(response) {
                if (response.success) {
                    modalAdicionarBalancoAdmin.hide();
                    recarregarComCacheBuster();
                }
            },
            error: function(xhr) {
                let msg = 'Erro ao salvar.';
                errorDiv.html(msg).show();
            }
        });
    });
    
    // Gatilho para o modal de ADICIONAR BALANÇO (data de hoje)
    $('#modalAdicionarBalancoAdmin').on('shown.bs.modal', function () {
        const dataInput = $(this).find('[name="data"]');
        if (!dataInput.val()) {
            const hoje = new Date().toISOString().split('T')[0];
            dataInput.val(hoje);
        }
    });

    // =================================================================
    // 9. GESTOR: LÓGICA DE EDIÇÃO (BALANÇO) - NOVO
    // =================================================================
    $('#tabelaGerenciarBalanco').on('click', '.btn-editar-balanco', function() {
        const pk = $(this).data('id');
        const form = $('#formEditarBalancoAdmin');
        const modalBody = form.find('.modal-body');
        
        form.attr('action', window.URL_ADMIN_EDITAR_BALANCO.replace('0', pk));
        modalBody.html('<p class="text-center"><i class="fas fa-spinner fa-spin"></i> Carregando...</p>');

        $.ajax({
            type: 'GET',
            url: window.URL_ADMIN_GET_BALANCO.replace('0', pk),
            success: function(data) {
                // Injeta o HTML do formulário de BALANÇO
                let formHtml = window.FORM_BALANCO_HTML
                    .replace(/<p>/g, '<div class="mb-3">').replace(/<\/p>/g, '</div>');
                
                let $tempHtml = $('<div>').html(formHtml);
                $tempHtml.find('label[for="id_usuario"]').closest('div.mb-3').remove();
                
                modalBody.html($tempHtml.html());
                
                // Preenche os dados
                form.find('[name="data"]').val(data.data);
                form.find('[name="loja"]').val(data.loja);
                form.find('[name="entrada"]').val(data.entrada);
                form.find('[name="saida"]').val(data.saida);
                
                if (data.anexo_url) {
                    form.find('[name="anexo"]').closest('.mb-3').append(
                        `<div class="mt-2 small">Anexo atual: <a href="${data.anexo_url}" target="_blank">Ver</a></div>`
                    );
                }

                $('#modalEditarBalancoAdmin .modal-title').html(`<i class="fas fa-boxes me-2"></i>Editar Balanço de <strong>${data.usuario_nome}</strong>`);
            },
            error: function() {
                modalBody.html('<p class="text-danger">Erro ao carregar dados.</p>');
            }
        });
    });

    $('#formEditarBalancoAdmin').on('submit', function(e) {
        e.preventDefault();
        const form = $(this)[0];
        const formData = new FormData(form);
        const btnSave = $(form).find('[type="submit"]');
        btnSave.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Salvando...');

        $.ajax({
            type: 'POST',
            url: $(form).attr('action'),
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                if (response.success) { 
                    modalEditarBalancoAdmin.hide();
                    recarregarComCacheBuster();
                }
            },
            error: function(xhr) {
                alert('Erro ao salvar.');
                btnSave.prop('disabled', false).html('Salvar Alterações');
            }
        });
    });

    // =================================================================
    // 10. GESTOR: EXCLUIR REGISTRO (BALANÇO) - NOVO
    // =================================================================
    $('#tabelaGerenciarBalanco').on('click', '.btn-excluir-balanco', function() {
        const pk = $(this).data('id');
        $('#formExcluirBalancoAdmin').attr('action', window.URL_ADMIN_DELETAR_BALANCO.replace('0', pk));
    });

    $('#formExcluirBalancoAdmin').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        $.ajax({
            type: 'POST',
            url: form.attr('action'),
            data: form.serialize(),
            success: function(response) {
                if (response.success) {
                    modalExcluirBalancoAdmin.hide();
                    recarregarComCacheBuster();
                }
            },
            error: function() { alert('Erro ao excluir.'); }
        });
    });

    // =================================================================
    // 11. FUNÇÃO GLOBAL DE RECARREGAMENTO (CACHE BUSTER)
    // =================================================================
    function recarregarComCacheBuster() {
        // Pega todos os valores dos filtros atuais do formulário
        const queryString = $('#form-filtros-jornada').serialize();
        // Adiciona um parâmetro de timestamp aleatório para enganar o cache
        const cacheBuster = '&_ts=' + new Date().getTime();
        // Define a nova URL do navegador, o que força um recarregamento total
        window.location.search = queryString + cacheBuster;
    }
});