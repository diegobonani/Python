/* static/js/gerenciar_veiculo.js */

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('form-veiculo');
    const tabelaContainer = document.getElementById('tabela-container');
    const btnCancelar = document.getElementById('btn-cancelar');
    const formTitulo = document.getElementById('form-titulo');
    const inputId = document.getElementById('veiculo_id');

    // =========================================================
    // 1. SALVAR (Adicionar ou Editar)
    // =========================================================
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Limpa erros visuais anteriores
            document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
            document.querySelectorAll('.invalid-feedback').forEach(el => el.textContent = '');

            const formData = new FormData(form);
            const url = form.action; // A URL vem do atributo action do form

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest' // Importante para o Django identificar AJAX
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    // Sucesso: Atualiza a tabela e limpa o form
                    tabelaContainer.innerHTML = data.html_tabela;
                    
                    // Mostra mensagem de sucesso (pode usar SweetAlert se tiver)
                    alert(data.message); 
                    
                    resetForm();
                } else if (data.status === 'error') {
                    // Erro de Validação: Mostra os erros nos campos
                    if (data.errors) {
                        for (const [fieldName, errorList] of Object.entries(data.errors)) {
                            // Procura o campo pelo name (ex: nome, marca, etc)
                            // O Django geralmente renderiza com id="id_nome", mas o name é "nome"
                            const field = form.querySelector(`[name="${fieldName}"]`);
                            if (field) {
                                field.classList.add('is-invalid');
                                // Tenta achar a div de erro próxima
                                const errorDiv = field.parentNode.querySelector('.invalid-feedback');
                                if (errorDiv) {
                                    errorDiv.textContent = errorList[0];
                                }
                            }
                        }
                    } else {
                        alert(data.message || 'Erro ao salvar.');
                    }
                }
            })
            .catch(error => {
                console.error('Erro na requisição:', error);
                alert('Erro de comunicação com o servidor.');
            });
        });
    }

    // =========================================================
    // 2. BOTÕES DA TABELA (Editar e Excluir)
    // =========================================================
    // Usamos Event Delegation no container da tabela, pois a tabela é recriada via AJAX
    if (tabelaContainer) {
        tabelaContainer.addEventListener('click', function(e) {
            // Verifica se clicou no botão ou no ícone dentro dele
            const btnEditar = e.target.closest('.btn-editar');
            const btnExcluir = e.target.closest('.btn-excluir');

            // --- LÓGICA DE EDITAR ---
            if (btnEditar) {
                const url = btnEditar.dataset.url; // URL para buscar os dados (JSON)
                
                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        // Preenche os campos do formulário com os IDs definidos no forms.py
                        if(inputId) inputId.value = data.id;
                        
                        // Campos de Texto/Número
                        setVal('id_nome', data.nome);
                        setVal('id_marca', data.marca);
                        setVal('id_modelo', data.modelo);
                        setVal('id_placa', data.placa);
                        setVal('id_ano', data.ano);
                        
                        setVal('id_consumo_cidade_gasolina', data.consumo_cidade_gasolina);
                        setVal('id_consumo_estrada_gasolina', data.consumo_estrada_gasolina);
                        setVal('id_consumo_cidade_etanol', data.consumo_cidade_etanol);
                        setVal('id_consumo_estrada_etanol', data.consumo_estrada_etanol);

                        // Ajusta a interface para modo de Edição
                        if(formTitulo) formTitulo.textContent = `Editar Veículo: ${data.nome}`;
                        if(btnCancelar) btnCancelar.style.display = 'inline-block';
                        
                        // Rola a página até o formulário
                        form.scrollIntoView({ behavior: 'smooth' });
                    })
                    .catch(err => console.error('Erro ao carregar dados:', err));
            }

            // --- LÓGICA DE EXCLUIR ---
            if (btnExcluir) {
                if (confirm('Tem certeza que deseja excluir este veículo?')) {
                    const url = btnExcluir.dataset.url;
                    // Pega o CSRF Token do formulário principal para usar na exclusão
                    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

                    fetch(url, {
                        method: 'POST',
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-CSRFToken': csrfToken
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'ok') {
                            tabelaContainer.innerHTML = data.html_tabela;
                            alert(data.message);
                            
                            // Se estava editando o veículo que acabou de excluir, limpa o form
                            if (inputId.value && url.includes(inputId.value)) {
                                resetForm();
                            }
                        } else {
                            alert('Erro ao excluir.');
                        }
                    });
                }
            }
        });
    }

    // =========================================================
    // 3. CANCELAR EDIÇÃO
    // =========================================================
    if (btnCancelar) {
        btnCancelar.addEventListener('click', function() {
            resetForm();
        });
    }

    // Função auxiliar para resetar o form
    function resetForm() {
        form.reset();
        if(inputId) inputId.value = ''; // Limpa o ID oculto
        if(formTitulo) formTitulo.textContent = 'Novo Veículo';
        if(btnCancelar) btnCancelar.style.display = 'none';
        
        // Remove classes de erro
        document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    }

    // Função auxiliar para setar valor de input com segurança
    function setVal(id, value) {
        const el = document.getElementById(id);
        if (el) el.value = value !== null ? value : '';
    }
});