$(document).ready(function() {
    console.log("Script Deslocamento - Edição Final (Inputs + Mapa).");

    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const TOM_TOM_KEY = window.TOM_TOM_API_KEY;

    // --- ELEMENTOS DOM ---
    const modalAdicionarEl = document.getElementById('modalAdicionarDeslocamento');
    const modalEditarEl = document.getElementById('modalEditarDeslocamento');
    const modalDetalhesEl = document.getElementById('modalDetalhesPercursos');

    // JQuery wrappers
    const $modalAdicionar = $(modalAdicionarEl);
    const formAdicionar = $('#formAdicionarDeslocamento');
    const formEditar = $('#formEditarDeslocamento');
    
    const waypointsContainerAdd = $('#waypoints-container');
    const waypointsContainerEdit = $('#waypoints-container-edit');
    
    const idEnderecosWaypoints = $('#id_enderecos_waypoints');
    const idEnderecosWaypointsEdit = $('#id_enderecos_waypoints_edit');

    const veiculoSelect = $('#id_veiculo');
    const consumoGroup = $('#consumo-group');
    const formErrors = $('#form-errors');
    const formErrorsEdit = $('#form-errors-edit');
    
    const detalhesBody = $('#detalhes-percurso-body');
    const tabelaContainer = $('#tabela-deslocamentos-container');

    // Contextos de Mapa
    const ctxCadastro = {
        tipo: 'cadastro',
        map: null, markers: [], containerList: waypointsContainerAdd, 
        modalId: '#modalAdicionarDeslocamento', mapId: 'map-cadastro', wrapperId: '#map-cadastro-wrapper'
    };
    
    const ctxEditar = {
        tipo: 'editar',
        map: null, markers: [], containerList: waypointsContainerEdit, 
        modalId: '#modalEditarDeslocamento', mapId: 'map-editar', wrapperId: '#map-editar-wrapper'
    };

    let mapDetalhe = null;

    // =================================================================
    // 1. FUNÇÕES DE MAPA E INPUTS
    // =================================================================

    function criarMapa(ctx) {
        if (ctx.map) { ctx.map.off(); ctx.map.remove(); ctx.map = null; }
        
        const divId = ctx.mapId;
        let parent = $(ctx.wrapperId);
        if(parent.length === 0) parent = $('#' + divId).parent();
        
        $('#' + divId).remove();
        const border = (ctx.tipo === 'editar') ? '2px solid #ffc107' : '2px solid #ddd';
        parent.append(`<div id="${divId}" style="height: 350px; width: 100%; border: ${border}; border-radius: 4px;"></div>`);

        setTimeout(() => {
            try {
                if(!document.getElementById(divId)) return;
                ctx.map = L.map(divId).setView([-23.026, -45.555], 13);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OSM' }).addTo(ctx.map);

                ctx.map.on('click', function(e) {
                    adicionarPonto(ctx, e.latlng.lat, e.latlng.lng);
                });
                ctx.map.invalidateSize();
            } catch (e) { console.error(`Erro mapa ${ctx.tipo}:`, e); }
        }, 300);
    }

    function adicionarPonto(ctx, lat, lng, enderecoTexto = null, inputExistente = null) {
        if (!ctx.map) return;

        const marker = L.marker([lat, lng], {draggable: true}).addTo(ctx.map);
        const markerId = L.stamp(marker);
        
        let input;
        
        // Se já passamos um input (caso da restauração de rota), usamos ele
        if (inputExistente) {
            const group = inputExistente.closest('.input-group');
            group.attr('data-marker-id', markerId);
            input = inputExistente;
        } else {
            // Senão cria um novo input visual
            const inputGroup = criarInputVisual(ctx, enderecoTexto || "", markerId);
            input = inputGroup.find('input');
        }
        
        ctx.markers.push({ marker: marker, input: input, id: markerId });

        if (!enderecoTexto) {
            input.val("Buscando...");
            fetch(`https://api.tomtom.com/search/2/reverseGeocode/${lat},${lng}.json?key=${TOM_TOM_KEY}`)
                .then(r => r.json())
                .then(data => { 
                    if(data.addresses && data.addresses.length > 0) {
                        const val = data.addresses[0].freeformAddress;
                        input.val(val); marker.bindPopup(val).openPopup();
                    } else { input.val(`${lat}, ${lng}`); }
                })
                .catch(() => input.val(`${lat}, ${lng}`));
        } else {
             marker.bindPopup(enderecoTexto);
             if(ctx.tipo === 'editar') ctx.map.panTo([lat, lng]);
        }

        marker.on('dragend', function() {
            const pos = marker.getLatLng();
            input.val("Atualizando...");
            fetch(`https://api.tomtom.com/search/2/reverseGeocode/${pos.lat},${pos.lng}.json?key=${TOM_TOM_KEY}`)
                .then(r => r.json()).then(data => { 
                    if(data.addresses && data.addresses.length > 0) {
                        input.val(data.addresses[0].freeformAddress); marker.bindPopup(data.addresses[0].freeformAddress); 
                    }
                });
        });
        
        updateWaypointLabels(ctx);
    }

    // --- FUNÇÃO CRÍTICA PARA EDIÇÃO: CARREGA ROTA EXISTENTE ---
    function carregarRotaNoFormulario(ctx, waypointsData) {
        // 1. Limpa lista visual e marcadores
        ctx.containerList.empty();
        if (ctx.map) { ctx.markers.forEach(m => ctx.map.removeLayer(m.marker)); }
        ctx.markers = [];

        // 2. Cria os INPUTS VISUAIS primeiro (Síncrono - Garante ordem e texto)
        const inputsCriados = [];
        
        if (waypointsData && waypointsData.length > 0) {
            waypointsData.forEach(wp => {
                // Cria o input JÁ com o texto do endereço
                const el = criarInputVisual(ctx, wp.address);
                inputsCriados.push({ element: el, address: wp.address });
            });
        } else {
            // Fallback se vazio
            criarInputVisual(ctx, "");
            criarInputVisual(ctx, "");
            return;
        }
        
        updateWaypointLabels(ctx);

        // 3. Busca coordenadas e coloca pinos no mapa (Assíncrono)
        // Aguarda o mapa estar pronto
        setTimeout(() => {
            if (!ctx.map) return;

            inputsCriados.forEach(item => {
                const input = item.element.find('input');
                const address = item.address;

                // Geocoding para achar onde colocar o pino
                fetch(`https://api.tomtom.com/search/2/search/${encodeURIComponent(address)}.json?key=${TOM_TOM_KEY}&limit=1&countrySet=BR`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.results && data.results.length > 0) {
                            const p = data.results[0].position;
                            // Chama adicionarPonto passando o input que JÁ criamos
                            adicionarPonto(ctx, p.lat, p.lon, address, input);
                        }
                    })
                    .catch(err => console.error("Erro geocoding restore:", err));
            });
        }, 600); // Delay um pouco maior para garantir que o mapa (L.map) inicializou
    }

    function criarInputVisual(ctx, valorInicial = "", markerId = null) {
        const html = `
            <div class="input-group mb-2" data-marker-id="${markerId || ''}">
                <span class="input-group-text small" style="width: 90px; cursor: grab;" title="Arraste para reordenar"></span>
                <input type="text" class="form-control form-control-sm waypoint-input" placeholder="Endereço..." value="${valorInicial}">
                <button class="btn btn-outline-danger btn-sm btn-remove-waypoint" data-tipo="${ctx.tipo}" type="button"><i class="fas fa-times"></i></button>
            </div>
        `;
        const el = $(html);
        
        // Insere antes do destino (se já houver lista)
        // Na carga de edição, queremos append sequencial simples se for inicialização
        const last = ctx.containerList.find('.input-group').last();
        const isDest = last.find('input').data('type') === 'destination';
        
        if (isDest && !markerId && valorInicial === "") {
             el.insertBefore(last); 
        } else {
             ctx.containerList.append(el);
        }
        
        enableAutocomplete(el.find('input'), ctx);
        
        // Botão remover específico deste input
        el.find('.btn-remove-waypoint').on('click', function() {
             const mId = el.attr('data-marker-id');
             if (mId && ctx.map) {
                 const p = ctx.markers.find(m => String(m.id) === String(mId));
                 if (p) ctx.map.removeLayer(p.marker);
                 ctx.markers = ctx.markers.filter(m => String(m.id) !== String(mId));
             }
             el.remove();
             updateWaypointLabels(ctx);
        });

        return el;
    }

    function enableAutocomplete(inputElement, ctx) {
        if (typeof $(inputElement).autocomplete !== "function") return;

        $(inputElement).autocomplete({
            source: function(request, response) {
                let center = "";
                if(ctx.map) { try{ const c = ctx.map.getCenter(); center = `&lat=${c.lat}&lon=${c.lng}&radius=10000`; }catch(e){} }
                
                $.ajax({
                    url: `https://api.tomtom.com/search/2/search/${encodeURIComponent(request.term)}.json?key=${TOM_TOM_KEY}&limit=5&countrySet=BR&language=pt-BR${center}`,
                    dataType: "json",
                    success: function(data) {
                        response($.map(data.results, function(item) {
                            let l = item.address.freeformAddress; if(item.poi?.name) l = item.poi.name + " - " + l;
                            return { label: l, value: l, lat: item.position.lat, lon: item.position.lon };
                        }));
                    }
                });
            },
            minLength: 3, delay: 500, appendTo: ctx.modalId,
            select: function(event, ui) {
                event.preventDefault(); $(this).val(ui.item.value);
                const group = $(this).closest('.input-group'); let mId = group.attr('data-marker-id');
                
                if (mId) {
                    const p = ctx.markers.find(m => String(m.id) === String(mId));
                    if (p) { p.marker.setLatLng([ui.item.lat, ui.item.lon]); ctx.map.panTo([ui.item.lat, ui.item.lon]); }
                } else if(ctx.map) {
                    const m = L.marker([ui.item.lat, ui.item.lon], {draggable:true}).addTo(ctx.map);
                    mId = L.stamp(m); group.attr('data-marker-id', mId);
                    ctx.markers.push({marker:m, input:$(this), id:mId});
                    ctx.map.setView([ui.item.lat, ui.item.lon], 16);
                    
                    m.on('dragend', function() {
                        const pos = m.getLatLng(); $(this).val("Atualizando...");
                        $.get(`https://api.tomtom.com/search/2/reverseGeocode/${pos.lat},${pos.lng}.json?key=${TOM_TOM_KEY}`, function(d){
                             if(d.addresses && d.addresses.length) $(this).val(d.addresses[0].freeformAddress);
                        }.bind(this));
                    });
                }
            }
        });
    }

    function updateWaypointLabels(ctx) {
        const items = ctx.containerList.find('.input-group');
        items.each(function(index) {
            let label = 'Parada'; let color = 'bg-warning text-dark'; let icon = '<i class="fas fa-map-pin"></i>';
            if (index === 0) { label = 'Origem'; color = 'bg-success text-white'; icon = '<i class="fas fa-dot-circle"></i>'; $(this).find('input').attr('data-type', 'origin'); }
            else if (index === items.length - 1) { label = 'Destino'; color = 'bg-danger text-white'; icon = '<i class="fas fa-flag-checkered"></i>'; $(this).find('input').attr('data-type', 'destination'); }
            else { $(this).find('input').attr('data-type', 'waypoint'); }
            $(this).find('.input-group-text').removeClass('bg-success bg-danger bg-warning text-white text-dark').addClass(color).html(`${icon} <span class="ms-1 fw-bold">${label}</span>`);
        });
    }

    // Init Sortables & Events
    if (waypointsContainerAdd.sortable) waypointsContainerAdd.sortable({ handle: '.input-group-text', update: () => updateWaypointLabels(ctxCadastro) });
    if (waypointsContainerEdit.sortable) waypointsContainerEdit.sortable({ handle: '.input-group-text', update: () => updateWaypointLabels(ctxEditar) });
    
    // Clique no label
    $(document).on('click', '.input-group-text', function() {
        const g = $(this).closest('.input-group'); const mId = g.attr('data-marker-id');
        const ctx = (g.parent().attr('id') === 'waypoints-container-edit') ? ctxEditar : ctxCadastro;
        if(mId && ctx.map) {
            const p = ctx.markers.find(m => String(m.id) === String(mId));
            if(p) { ctx.map.flyTo(p.marker.getLatLng(), 16); p.marker.openPopup(); }
        } else g.find('input').focus();
    });

    $('#btnAddWaypoint').on('click', () => { criarInputVisual(ctxCadastro); updateWaypointLabels(ctxCadastro); });
    $('#btnAddWaypointEdit').on('click', () => { criarInputVisual(ctxEditar); updateWaypointLabels(ctxEditar); });

    function toggleConsumoGroup() { $('#consumo-group').toggle(!veiculoSelect.val()); }
    veiculoSelect.on('change', toggleConsumoGroup);

    // =================================================================
    // 2. ABERTURA CADASTRO
    // =================================================================
    $modalAdicionar.on('shown.bs.modal', function() {
        formAdicionar[0].reset();
        $('#form-errors').addClass('d-none');
        ctxCadastro.markers = [];
        ctxCadastro.containerList.empty();
        
        const def = window.DEFAULT_ORIGIN_ADDRESS || "Av. João Ramalho, 409, Taubaté - SP";
        criarInputVisual(ctxCadastro, def);
        criarInputVisual(ctxCadastro, "");
        
        updateWaypointLabels(ctxCadastro);
        criarMapa(ctxCadastro);
    });

    // =================================================================
    // 3. ABERTURA EDIÇÃO
    // =================================================================
    $(document).on('click', '.btn-editar', function() {
        const id = $(this).data('id');
        const urlJson = window.URL_GET_JSON.replace('0', id);
        const urlEdit = window.URL_EDITAR_DESLOCAMENTO.replace('0', id);
        
        formEditar.attr('action', urlEdit);
        $('#form-errors-edit').addClass('d-none');
        
        const modalInstance = bootstrap.Modal.getOrCreateInstance(modalEditarEl);
        modalInstance.show();
        
        ctxEditar.containerList.html('<div class="text-center my-3"><i class="fas fa-spinner fa-spin"></i> Carregando...</div>');
        criarMapa(ctxEditar);

        $.get(urlJson, function(data) {
            $('#formEditarDeslocamento [name="data"]').val(data.data);
            $('#formEditarDeslocamento [name="veiculo"]').val(data.veiculo_id);
            $('#formEditarDeslocamento [name="tipo_combustivel"]').val(data.tipo_combustivel);
            $('#formEditarDeslocamento [name="tipo_trajeto"]').val(data.tipo_trajeto);
            $('#formEditarDeslocamento [name="valor_litro"]').val(data.valor_litro);
            $('#formEditarDeslocamento [name="observacoes"]').val(data.observacoes);
            if(data.consumo_manual) $('#formEditarDeslocamento [name="consumo_manual"]').val(data.consumo_manual);
            
            // Popula rota visualmente e depois mapa
            carregarRotaNoFormulario(ctxEditar, data.waypoints);
            
        }).fail(function() { alert("Erro ao buscar dados."); modalInstance.hide(); });
    });

    // =================================================================
    // 4. SUBMITS, FILTROS, TABELA (Mantido)
    // =================================================================
    // ... (Copie a função handleFormSubmit, lógica de filtros e DataTable do código anterior. Elas estão corretas) ...
    // Para economizar espaço aqui, estou focando na correção do Mapa e Inputs Padrão.
    // Mas certifique-se de incluir a lógica de filtros que te mandei antes.
    
    // Filtros
    function getLocalDateString(date) {
        const year = date.getFullYear(); const month = String(date.getMonth() + 1).padStart(2, '0'); const day = String(date.getDate()).padStart(2, '0'); return `${year}-${month}-${day}`;
    }
    function processarFiltros() {
        const tipo = $('#filtro_tipo').val(); let inicio = ''; let fim = ''; const hoje = new Date();
        if (tipo === 'hoje') { inicio = getLocalDateString(hoje); fim = inicio; }
        else if (tipo === 'ontem') { const ontem = new Date(hoje); ontem.setDate(hoje.getDate()-1); inicio = getLocalDateString(ontem); fim = inicio; }
        else if (tipo === 'mes_atual') { inicio = getLocalDateString(new Date(hoje.getFullYear(), hoje.getMonth(), 1)); fim = getLocalDateString(new Date(hoje.getFullYear(), hoje.getMonth()+1, 0)); }
        else if (tipo === 'dia_especifico') { inicio = $('#input_dia_especifico').val(); fim = inicio; }
        else if (tipo === 'mes_especifico') { const m = $('#input_mes_especifico').val(); if(m) { const [a, mm] = m.split('-'); inicio = `${a}-${mm}-01`; fim = `${a}-${mm}-${new Date(a,mm,0).getDate()}`; } }
        else if (tipo === 'periodo') { inicio = $('#input_periodo_inicio').val(); fim = $('#input_periodo_fim').val(); }
        $('#filtro_data_inicio').val(inicio); $('#filtro_data_fim').val(fim);
    }
    $('#filtro_tipo').on('change', function() {
        const tipo = $(this).val(); $('.filtro-container').addClass('d-none');
        $('#input_dia_especifico, #input_mes_especifico, #input_periodo_inicio, #input_periodo_fim').val('');
        if (tipo === 'dia_especifico') $('#container-dia').removeClass('d-none'); else if (tipo === 'mes_especifico') $('#container-mes').removeClass('d-none'); else if (tipo === 'periodo') $('#container-periodo').removeClass('d-none');
        if (['hoje', 'ontem', 'mes_atual', 'todos'].includes(tipo)) carregarTabela();
    });
    $('#input_dia_especifico, #input_mes_especifico, #input_periodo_inicio, #input_periodo_fim').on('change', function() {
        if ($('#filtro_tipo').val() === 'periodo') { if ($('#input_periodo_inicio').val() && $('#input_periodo_fim').val()) carregarTabela(); } else carregarTabela();
    });

    function handleFormSubmit(form, ctx, inputHiddenSelector) {
        form.on('submit', function(e) {
            e.preventDefault();
            const errDiv = form.find('.alert-danger'); errDiv.addClass('d-none');
            const wps = []; ctx.containerList.find('input').each(function() { if($(this).val().trim()) wps.push({address: $(this).val().trim()}); });
            if (form.attr('id') === 'formAdicionarDeslocamento' && wps.length < 2) { errDiv.text("Defina Origem e Destino.").removeClass('d-none'); return; }
            $(inputHiddenSelector).val(JSON.stringify(wps));
            const btn = form.find('button[type="submit"]'); const txt = btn.html(); btn.prop('disabled', true).html('Processando...');
            $.ajax({
                type: 'POST', url: form.attr('action'), data: form.serialize(), headers: {'X-CSRFToken': csrftoken},
                success: function(res) {
                    if (res.confirm_needed) {
                        if(confirm(res.message)) {
                             const newData = form.serialize()+"&force_save=true";
                             $.ajax({ type:'POST', url:form.attr('action'), data:newData, headers:{'X-CSRFToken':csrftoken}, 
                                 success: function(r){ alert(r.message); bootstrap.Modal.getInstance(ctx.modalEl).hide(); carregarTabela(); },
                                 complete: function() { btn.prop('disabled', false).html(txt); }
                             });
                        } else { btn.prop('disabled', false).html(txt); }
                    } else { alert(res.message); bootstrap.Modal.getInstance(ctx.modalEl).hide(); carregarTabela(); }
                },
                error: function(xhr) {
                    let msg = xhr.responseJSON?.message || 'Erro.'; if(xhr.responseJSON?.errors) msg = JSON.stringify(xhr.responseJSON.errors);
                    errDiv.html(msg).removeClass('d-none'); btn.prop('disabled', false).html(txt);
                }
            });
        });
    }
    handleFormSubmit(formAdicionar, ctxCadastro, '#id_enderecos_waypoints');
    handleFormSubmit(formEditar, ctxEditar, '#id_enderecos_waypoints_edit');

    // =================================================================
    // 5. TABELA E DETALHES
    // =================================================================
    function initializeDataTable() {
        if ($('#tabela-deslocamentos').length === 0) return;
        if ($.fn.DataTable.isDataTable('#tabela-deslocamentos')) return;
        $('#tabela-deslocamentos').DataTable({
            language: { url: window.DATATABLES_LANGUAGE_URL, emptyTable: "Nenhum registro encontrado.", zeroRecords: "Nada encontrado." },
            "order": [[ 0, "desc" ]], "autoWidth": false, "scrollX": true, "responsive": false, "paging": false,
            "columnDefs": [{ "orderable": false, "targets": 8 }],
            "footerCallback": function (row, data, start, end, display) {
                var api = this.api();
                var intVal = function (i) { return typeof i === 'string' ? i.replace(/[\R\$\s]|km|min|'/g, '').replace(',', '.') * 1 : typeof i === 'number' ? i : 0; };
                var totalKm = api.column(5, {page: 'current'}).data().reduce((a, b) => intVal(a) + intVal(b), 0);
                var totalTempo = api.column(6, {page: 'current'}).data().reduce((a, b) => intVal(a) + intVal(b), 0);
                var totalCusto = api.column(7, {page: 'current'}).data().reduce((a, b) => intVal(a) + intVal(b), 0);
                $(api.column(5).footer()).html(totalKm.toFixed(1).replace('.', ',') + ' km');
                let ts = totalTempo + " min"; if(totalTempo > 60) ts = `${Math.floor(totalTempo/60)}h ${totalTempo%60}min`;
                $(api.column(6).footer()).html(ts);
                $(api.column(7).footer()).html('R$ ' + totalCusto.toFixed(2).replace('.', ','));
            }
        });
    }

    function carregarTabela() {
        processarFiltros();
        const inicio = $('#filtro_data_inicio').val(); const fim = $('#filtro_data_fim').val();
        tabelaContainer.html('<div class="text-center p-4"><div class="spinner-border text-primary"></div><div class="mt-2 text-muted">Carregando...</div></div>');
        const url = `${window.URL_TABELA_DESLOCAMENTOS}?data_inicio=${inicio}&data_fim=${fim}`;
        tabelaContainer.load(url, function() { 
            if($.fn.DataTable.isDataTable('#tabela-deslocamentos')) $('#tabela-deslocamentos').DataTable().destroy(); 
            initializeDataTable(); 
        });
    }
    
    // Inicia com Mês Atual
    $('#filtro_tipo').val('mes_atual').trigger('change');

    $('#btn-filtrar').on('click', carregarTabela);
    $('#btn-limpar').on('click', function() { $('#filtro_tipo').val('todos').trigger('change'); });

    // Detalhes
    $(document).on('click', '.btn-detalhes, .btn-ver-rota', function(e) {
        e.preventDefault(); const id = $(this).data('id'); const url = window.URL_DETALHES_PERCURSO.replace('0', id);
        if(mapDetalhe){mapDetalhe.off();mapDetalhe.remove();mapDetalhe=null;}
        detalhesBody.html('<div class="text-center p-5"><i class="fas fa-spinner fa-spin fa-2x text-primary"></i></div>');
        bootstrap.Modal.getOrCreateInstance(modalDetalhesEl).show();
        $.ajax({url:url, method:'GET', success:function(html){
            detalhesBody.html(html);
            setTimeout(()=>{
                const elMap = document.getElementById('map-detalhe');
                if(elMap){
                    const p = elMap.parentNode; p.removeChild(elMap); const n = document.createElement('div'); n.id='map-detalhe'; n.style.height='450px'; n.style.width='100%'; p.insertBefore(n, p.firstChild);
                    try{
                        mapDetalhe = L.map('map-detalhe'); L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OSM' }).addTo(mapDetalhe);
                        const sd = document.getElementById('waypoints-data');
                        if(sd){
                            const wd = JSON.parse(sd.textContent); const ll = []; let pen = wd.length;
                            wd.forEach((wp,i)=>{
                                fetch(`https://api.tomtom.com/search/2/search/${encodeURIComponent(wp.address)}.json?key=${TOM_TOM_KEY}&limit=1&countrySet=BR`).then(r=>r.json()).then(d=>{
                                    if(d.results && d.results.length){ const p=d.results[0].position; L.marker([p.lat, p.lon]).addTo(mapDetalhe).bindPopup(`<b>${i+1}. ${wp.type}</b><br>${wp.address}`); ll.push([p.lat, p.lon]); }
                                    pen--; if(pen===0 && ll.length>0){ L.polyline(ll, {color:'blue'}).addTo(mapDetalhe); mapDetalhe.fitBounds(ll); mapDetalhe.invalidateSize(); }
                                });
                            });
                        }
                    }catch(e){}
                }
            }, 500);
        }});
    });
    
    $(document).on('click', '.btn-excluir', function() {
        if(!confirm('Confirma exclusão?')) return;
        $.ajax({ url: `/deslocamento/deletar/${$(this).data('id')}/`, method: 'POST', headers: {'X-CSRFToken': csrftoken}, success: function() { carregarTabela(); } });
    });
});