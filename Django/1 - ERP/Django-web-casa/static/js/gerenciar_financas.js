/**
 * FINANCE MANAGER PRO - V24.2 (FIXED)
 * -------------------------------------------------------------------------
 * - Correção DEFINITIVA do NaN (Regex Global para parse de BRL)
 * - DataTables para Lançamentos (AJAX)
 * - Lógica Completa de Veículos
 * - Filtros Visuais de Contas e Tipos
 * - CRUD Completo
 * -------------------------------------------------------------------------
 */

$(document).ready(function() {
    "use strict";
    console.log(">>> Gerenciador Financeiro Iniciado (V24.2 Fixed)...");

    // =========================================================================
    // 1. UTILITÁRIOS E CONFIGURAÇÃO
    // =========================================================================

    const Config = {
        urls: {
            tabela: window.URL_TABELA_FINANCAS,
            categorias: window.URL_GET_CATEGORIAS || window.URL_GET_CATEGORIAS_TIPO,
            servicosVeiculo: window.URL_GET_SERVICOS_VEICULO,
            veiculoKm: window.URL_GET_VEICULO_KM,
            simulacao: window.URL_ABA_SIMULACAO_FINANCAS,
            
            getUrlJson: (pk) => window.URL_GET_LANCAMENTO_JSON.replace('0', pk),
            getUrlEditar: (pk) => window.URL_EDITAR_LANCAMENTO.replace('0', pk),
            getUrlDeletar: (pk) => window.URL_DELETAR_LANCAMENTO.replace('0', pk)
        },
        constants: {
            categoriaCarroId: window.CATEGORIA_CARRO_ID 
        },
        dtLang: window.DATATABLES_LANGUAGE_URL || '//cdn.datatables.net/plug-ins/1.13.11/i18n/pt-BR.json'
    };

    const Utils = {
        // --- A CORREÇÃO DO NaN ESTÁ AQUI ---
        parseMoney: (val) => {
            // 1. Proteção contra valores nulos/indefinidos
            if (val === undefined || val === null || val === '') return 0.0;
            
            // 2. Garante que é string para manipular
            let str = String(val);

            // 3. Se já for um número JS puro, retorna direto
            if (typeof val === 'number') return val;

            // 4. Se tiver vírgula, assumimos que é PT-BR (ex: 1.500,50 ou 1500,50)
            if (str.includes(',')) {
                // Remove TODOS os pontos de milhar (Regex Global /\./g)
                str = str.replace(/\./g, ''); 
                // Troca a vírgula decimal por ponto
                str = str.replace(',', '.');
            }
            
            // 5. Converte para Float e garante que retorna 0.0 se falhar
            return parseFloat(str) || 0.0;
        },
        
        formatBRL: (val) => {
            return val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        },

        showToast: (msg) => {
            const toastEl = document.getElementById('successToast');
            if (toastEl) {
                $('#successToastBody').text(msg);
                new bootstrap.Toast(toastEl).show();
            } else { alert(msg); }
        },

        getModal: (id) => {
            const el = document.getElementById(id);
            return el ? new bootstrap.Modal(el) : null;
        }
    };

    // Inicializa Select2
    $('#filtro-contas').select2({
        theme: 'bootstrap-5',
        width: '100%',
        placeholder: "Selecione as contas...",
        allowClear: true
    });

    // =========================================================================
    // 2. LÓGICA DE SALDOS (ATUALIZADA)
    // =========================================================================

    const SaldoManager = {
        init: function() {
            $('#filtro-contas').on('change', this.atualizarVisibilidade);
            // Pequeno delay para garantir que o DOM renderizou os data-attributes
            setTimeout(() => this.atualizarVisibilidade(), 100);
        },

        atualizarVisibilidade: function() {
            const selecionados = $('#filtro-contas').val() || [];
            let total = 0.0;
            let countVisible = 0;

            $('.card-conta-wrapper').each(function() {
                const $card = $(this);
                const contaId = String($card.data('id'));
                // Pega o valor cru do atributo HTML
                const rawSaldo = $card.attr('data-saldo'); 

                const deveMostrar = (selecionados.length === 0) || selecionados.includes(contaId);

                if (deveMostrar) {
                    $card.fadeIn(200);
                    // Usa a nova função robusta para somar
                    total += Utils.parseMoney(rawSaldo);
                    countVisible++;
                } else {
                    $card.hide();
                }
            });

            const $cardTotal = $('#card-total-saldos');
            const $valorTotal = $('#valor-total-selecionado');
            
            // Atualiza o texto formatado
            $valorTotal.text(Utils.formatBRL(total));
            
            // Ajusta cor verde/vermelho
            if (total >= 0) $valorTotal.removeClass('text-danger').addClass('text-success');
            else $valorTotal.removeClass('text-success').addClass('text-danger');

            if (countVisible > 0 && selecionados.length > 0) $cardTotal.fadeIn();
            else $cardTotal.hide();
        }
    };

    // =========================================================================
    // 3. LÓGICA DE VEÍCULOS (CARRO)
    // =========================================================================

    const VehicleManager = {
        toggleCampos: function($form) {
            const $categoriaSelect = $form.find('#id_categoria');
            const $container = $form.find('.campos-carro-container');
            const $camposIndividuais = $form.find('#id_veiculo, #id_km_odometro, #id_servico_realizado, #id_litros').closest('p, div.mb-3');

            if ($categoriaSelect.val() == Config.constants.categoriaCarroId) {
                if ($container.length) $container.slideDown();
                else $camposIndividuais.slideDown();
            } else {
                if ($container.length) $container.slideUp();
                else $camposIndividuais.slideUp();
            }
        },

        atualizarServicosKm: function($form, servicoSelecionadoId = null) {
            const veiculoId = $form.find('#id_veiculo').val();
            const $servicoSelect = $form.find('#id_servico_realizado');
            const $kmInput = $form.find('#id_km_odometro');

            if (!veiculoId) {
                $servicoSelect.empty().append('<option value="">---------</option>').prop('disabled', true);
                $kmInput.attr('placeholder', 'KM no painel');
                return;
            }

            $servicoSelect.prop('disabled', true).empty().append('<option value="">Carregando...</option>');

            if (Config.urls.servicosVeiculo) {
                $.ajax({
                    url: Config.urls.servicosVeiculo,
                    data: { 'veiculo_id': veiculoId },
                    success: function(data) {
                        $servicoSelect.empty().append('<option value="">Nenhum (só abastecimento)</option>');
                        data.forEach(function(servico) {
                            $servicoSelect.append(new Option(servico.nome, servico.id));
                        });
                        $servicoSelect.prop('disabled', false);
                        if (servicoSelecionadoId) $servicoSelect.val(servicoSelecionadoId);
                    }
                });
            }

            if (Config.urls.veiculoKm) {
                $.ajax({
                    url: Config.urls.veiculoKm,
                    data: { 'veiculo_id': veiculoId },
                    success: function(data) {
                        $kmInput.attr('placeholder', `Último KM registrado: ${data.km_atual}`);
                    }
                });
            }
        }
    };

    // =========================================================================
    // 4. DATATABLES E ABA DE LANÇAMENTOS
    // =========================================================================

    const FinancaTable = {
        reload: function(contaId = null) {
            const tipo = $('#filtro-tipo').val(); 
            const $container = $('#tabela-financas-container');
            let url = `${Config.urls.tabela}?tipo_filtro=${tipo}`;
            if (contaId) url += `&conta_id=${contaId}`;

            $container.html(`
                <div class="loading-overlay">
                    <div class="spinner-border text-primary"></div>
                    <p class="mt-2 text-muted">Carregando transações...</p>
                </div>
            `);

            $container.load(url, function() {
                if ($('#tabela-financas').length) {
                    $('#tabela-financas').DataTable({
                        responsive: true,
                        language: { url: Config.dtLang },
                        order: [[0, 'desc']], 
                        pageLength: 25,
                        columnDefs: [{ targets: -1, orderable: false }]
                    });
                }
            });
        }
    };

    // =========================================================================
    // 5. CRUD E EVENTOS GLOBAIS
    // =========================================================================

    const FormHandler = {
        init: function() {
            // Lógica de Categorias Dinâmicas
            $(document).on('change', '#id_conta_tipo, #id_tipo', function() {
                const tipo = $(this).val(); 
                const $form = $(this).closest('form');
                const $catSelect = $form.find('#id_categoria');
                
                $catSelect.html('<option>Carregando...</option>').prop('disabled', true);
                
                if (!tipo) {
                    $catSelect.html('<option value="">Selecione o Tipo</option>');
                    return;
                }

                $.ajax({
                    url: Config.urls.categorias,
                    data: { tipo: tipo },
                    success: function(data) {
                        $catSelect.empty().append(new Option('---------', ''));
                        data.forEach(function(cat) {
                            $catSelect.append(new Option(cat.nome, cat.id));
                        });
                        $catSelect.prop('disabled', false);
                    }
                });
            });

            // Veículos
            const $forms = $('#formAdicionarLancamento, #formEditarLancamento');
            $forms.on('change', '#id_categoria', function() { VehicleManager.toggleCampos($(this).closest('form')); });
            $forms.on('change', '#id_veiculo', function() { VehicleManager.toggleCampos($(this).closest('form')); VehicleManager.atualizarServicosKm($(this).closest('form')); });

            // Abrir Modal Adicionar
            $('#modalAdicionarLancamento').on('show.bs.modal', function(e) {
                if (e.relatedTarget && $(e.relatedTarget).hasClass('btn-editar-lancamento')) return;
                const $form = $('#formAdicionarLancamento');
                $form[0].reset();
                $form.find('#id_categoria').empty().append('<option value="">Selecione um Tipo</option>');
                VehicleManager.toggleCampos($form);
                $form.find('.alert-danger').hide();
            });

            // Botão Editar
            $(document).on('click', '.btn-editar-financa, .btn-editar-lancamento', function() {
                const id = $(this).data('id');
                const $form = $('#formEditarLancamento');
                $form.attr('action', Config.urls.getUrlEditar(id));
                $form.find('.alert-danger').hide();

                $.ajax({
                    url: Config.urls.getUrlJson(id),
                    success: function(data) {
                        $form.find('#id_descricao').val(data.descricao);
                        // Converte para formato numérico simples para o input type="number" ou text
                        // Se o input espera 1200.50, usamos parseMoney. 
                        // Se o Django form espera 1200,50, usamos valor direto. 
                        // Geralmente input de form HTML lida melhor com 1200.50 ou valor original do backend.
                        $form.find('#id_valor').val(data.valor); 
                        
                        $form.find('#id_data_lancamento, #id_data_registro').val(data.data_lancamento || data.data_registro);
                        $form.find('#id_conta').val(data.conta_id);
                        $form.find('#id_pago').prop('checked', data.pago);
                        $form.find('#id_fixo').prop('checked', data.fixo);
                        $form.find('#id_forma_pagamento').val(data.forma_pagamento_id);

                        const tipoVal = data.tipo || data.conta_tipo;
                        $form.find('#id_tipo, #id_conta_tipo').val(tipoVal);

                        const $catSelect = $form.find('#id_categoria');
                        $.ajax({
                            url: Config.urls.categorias,
                            data: { tipo: tipoVal },
                            success: function(cats) {
                                $catSelect.empty();
                                cats.forEach(c => $catSelect.append(new Option(c.nome, c.id)));
                                $catSelect.val(data.categoria_id);
                                VehicleManager.toggleCampos($form);
                                if (data.categoria_id == Config.constants.categoriaCarroId) {
                                    $form.find('#id_veiculo').val(data.veiculo_id);
                                    $form.find('#id_km_odometro').val(data.km_odometro);
                                    $form.find('#id_litros').val(data.litros);
                                    VehicleManager.atualizarServicosKm($form, data.servico_realizado_id);
                                }
                                Utils.getModal('modalEditarLancamento').show();
                            }
                        });
                    }
                });
            });

            // Excluir
            $(document).on('click', '.btn-excluir-financa, .btn-excluir-lancamento', function() {
                const id = $(this).data('id');
                $('#formExcluirLancamento').attr('action', Config.urls.getUrlDeletar(id));
                Utils.getModal('modalConfirmarExclusaoLancamento').show();
            });

            // Submit Geral
            $('form[action*="/financas/"]').on('submit', function(e) {
                if ($(this).attr('method') === 'get') return;
                e.preventDefault();
                const $form = $(this);
                const $modal = $form.closest('.modal');
                const formData = new FormData(this);

                // Força conversão de valor para formato float aceito pelo Django se necessário
                // Mas geralmente o Django lida bem com formData padrão.

                $.ajax({
                    type: 'POST',
                    url: $form.attr('action'),
                    data: formData,
                    processData: false,
                    contentType: false,
                    success: function(res) {
                        if (res.success) {
                            if ($modal.length) $modal.modal('hide');
                            $form[0].reset();
                            Utils.showToast(res.message || "Sucesso!");
                            FinancaTable.reload();
                            setTimeout(() => location.reload(), 800); // Recarrega saldos
                        } else {
                            const $errorDiv = $form.find('.alert-danger');
                            let msg = "<ul>";
                            if (res.errors) {
                                for (let k in res.errors) { msg += `<li>${k}: ${res.errors[k]}</li>`; }
                            } else { msg += "<li>Erro desconhecido</li>"; }
                            msg += "</ul>";
                            if ($errorDiv.length) $errorDiv.html(msg).show();
                            else alert("Erro: verifique os campos.");
                        }
                    },
                    error: function(xhr) { alert('Erro servidor: ' + xhr.status); }
                });
            });
        }
    };

    // --- EVENTOS DE ABA ---
    const toggleActionButton = (abaId) => {
        const btn = $('#btn-novo-lancamento');
        if (abaId === 'lancamentos-tab') btn.fadeIn();
        else btn.fadeOut();
    };

    $('button[data-bs-toggle="tab"]').on('shown.bs.tab', function(e) {
        const novaAba = $(e.target).attr('id');
        toggleActionButton(novaAba);
        $.fn.dataTable.tables({ visible: true, api: true }).columns.adjust().responsive.recalc();

        if (novaAba === 'lancamentos-tab') FinancaTable.reload();
        else if (novaAba === 'simulacao-fin-tab' && Config.urls.simulacao) {
            $('#simulacao-fin-container').load(Config.urls.simulacao);
        }
    });

    $('#filtro-tipo').on('change', function() { FinancaTable.reload(); });
    
    $('#saldos-pane').on('click', '.btn-ver-transacoes', function(e) {
        e.preventDefault();
        const contaId = $(this).data('conta-id');
        const tabTrigger = new bootstrap.Tab(document.getElementById('lancamentos-tab'));
        tabTrigger.show();
        FinancaTable.reload(contaId);
    });

    // Boot
    SaldoManager.init();
    FormHandler.init();
    if ($('#lancamentos-tab').hasClass('active')) {
        $('#btn-novo-lancamento').show();
        FinancaTable.reload();
    } else {
        $('#btn-novo-lancamento').hide();
    }
});