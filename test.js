
        // Configuración y variables del Calendario
        let currentYear = 2026;
        let currentMonth = 5; // Junio (0-indexed en JS)
        const monthNames = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ];
        let allMateriaOptions = [];
        let editingParcialId = null;
        let allHorarioMateriaOptions = [];
        let editingHorarioId = null;

        document.addEventListener("DOMContentLoaded", () => {
            // Animación suave de la barra de progreso al cargar la página
            const progressBar = document.getElementById("progressBar");
            const targetWidth = progressBar.getAttribute("data-progress");
            setTimeout(() => {
                progressBar.style.width = targetWidth + "%";
            }, 200);

            // Guardar opciones de materias para el buscador del modal de parciales
            const select = document.getElementById('parcialMateria');
            if (select) {
                allMateriaOptions = Array.from(select.options).map(opt => ({
                    value: opt.value,
                    text: opt.text,
                    disabled: opt.disabled,
                    selected: opt.selected
                }));
            }

            // Guardar opciones de materias para el buscador del modal de horarios
            const horarioSelect = document.getElementById('horarioMateria');
            if (horarioSelect) {
                allHorarioMateriaOptions = Array.from(horarioSelect.options).map(opt => ({
                    value: opt.value,
                    text: opt.text,
                    disabled: opt.disabled,
                    selected: opt.selected
                }));
            }

            // Inicializar calendario y formateo de parciales
            const today = new Date();
            currentYear = today.getFullYear();
            currentMonth = today.getMonth();
            formatParcialDates();
            renderCalendar();
            updateCountdowns();
            setInterval(updateCountdowns, 1000);
        });

        // Función para colapsar/desplegar años en el plan de estudios
        function toggleNivel(nivelHeader) {
            const grupo = nivelHeader.closest('.nivel-grupo');
            grupo.classList.toggle('collapsed');
        }

        // Función para colapsar/desplegar paneles de la columna izquierda
        function toggleLeftPanel(header) {
            const panel = header.closest('.collapsible-panel');
            if (panel) {
                panel.classList.toggle('collapsed');
            }
        }

        // Función AJAX para actualizar la nota final
        async function updateMateriaNota(materiaId, nota) {
            try {
                const response = await fetch("/update-nota", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        materia_id: materiaId,
                        nota: nota
                    })
                });

                const result = await response.json();
                
                if (result.success) {
                    showToast(`¡Nota actualizada correctamente!`);
                    
                    // Esperamos un instante y refrescamos la página para recalcular promedios
                    setTimeout(() => {
                        location.reload();
                    }, 800);
                } else {
                    showToast("Error: " + result.message, true);
                }
            } catch (error) {
                console.error("Error al actualizar la nota:", error);
                showToast("Error de conexión con el servidor", true);
            }
        }

        // Función AJAX para ajustar el contador de veces cursada de forma instantánea
        async function adjustVecesCursada(materiaId, delta, currentVal) {
            const btn = event ? event.currentTarget : null;
            const container = btn ? btn.parentElement : null;
            const textSpan = container ? container.querySelector('span') : null;
            
            const newVal = Math.max(0, currentVal + delta);
            
            // Si no cambia (ya está en 0 y restamos), no hacemos nada
            if (newVal === currentVal) return;
            
            // Actualizar interfaz al instante para máxima fluidez
            if (textSpan) {
                textSpan.textContent = newVal;
            }
            
            try {
                const response = await fetch("/update-veces-cursada", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        materia_id: materiaId,
                        veces_cursada: newVal
                    })
                });

                const result = await response.json();
                if (result.success) {
                    showToast(`Cursadas actualizadas a ${newVal}`);
                    // Actualizar el atributo onclick para reflejar el nuevo valor en futuras interacciones
                    if (container) {
                        const buttons = container.querySelectorAll('button');
                        if (buttons.length === 2) {
                            buttons[0].setAttribute('onclick', `adjustVecesCursada(${materiaId}, -1, ${newVal})`);
                            buttons[1].setAttribute('onclick', `adjustVecesCursada(${materiaId}, 1, ${newVal})`);
                        }
                    }
                } else {
                    showToast("Error: " + result.message, true);
                    // Revertir en caso de error
                    if (textSpan) textSpan.textContent = currentVal;
                }
            } catch (error) {
                console.error("Error al actualizar cursadas:", error);
                showToast("Error de conexión con el servidor", true);
                if (textSpan) textSpan.textContent = currentVal;
            }
        }

        // Función AJAX para actualizar el estado sin recargas bruscas
        async function updateMateriaEstado(materiaId, nuevoEstado) {
            try {
                const response = await fetch("/update-estado", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        materia_id: materiaId,
                        nuevo_estado: nuevoEstado
                    })
                });

                const result = await response.json();
                
                if (result.success) {
                    showToast(`¡Materia actualizada a ${nuevoEstado}!`);
                    
                    // Esperamos una pequeña fracción de segundo para que el usuario aprecie el cambio en el botón y refrescamos los cálculos en el backend
                    setTimeout(() => {
                        location.reload();
                    }, 800);
                } else {
                    showToast("Error: " + result.message, true);
                }
            } catch (error) {
                console.error("Error al actualizar la materia:", error);
                showToast("Error de conexión con el servidor", true);
            }
        }

        // ==========================================
        // FUNCIONES DE CALENDARIO Y AGENDA DE PARCIALES
        // ==========================================

        // Obtener todos los parciales programados desde el DOM pre-renderizado por Jinja2
        function getScheduledParciales() {
            const cards = document.querySelectorAll('.parcial-card');
            const list = [];
            cards.forEach(card => {
                list.push({
                    id: parseInt(card.getAttribute('data-parcial-id')),
                    fechaIso: card.getAttribute('data-fecha-iso'),
                    nombre: card.querySelector('.parcial-name').textContent,
                    materia: card.querySelector('.parcial-materia-title').textContent
                });
            });
            return list;
        }

        // Formatear las fechas raw en español amigable
        function formatParcialDates() {
            const dateSpans = document.querySelectorAll('.parcial-date-formatted');
            dateSpans.forEach(span => {
                const raw = span.getAttribute('data-raw-date');
                if (raw) {
                    const date = new Date(raw);
                    const options = { weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' };
                    // Capitalizar primer letra del día de semana
                    let formatted = date.toLocaleDateString('es-AR', options);
                    formatted = formatted.charAt(0).toUpperCase() + formatted.slice(1);
                    span.textContent = formatted;
                }
            });
        }

        // Renderizar el Calendario del Mes seleccionado
        function renderCalendar() {
            const calendarDaysGrid = document.getElementById('calendarDaysGrid');
            const calendarMonthYear = document.getElementById('calendarMonthYear');
            if (!calendarDaysGrid || !calendarMonthYear) return;

            calendarMonthYear.textContent = `${monthNames[currentMonth]} ${currentYear}`;
            calendarDaysGrid.innerHTML = '';

            // Obtener el primer día de la semana del mes (0 = Domingo, ..., 6 = Sábado)
            const firstDayIndex = new Date(currentYear, currentMonth, 1).getDay();
            // Obtener el total de días en el mes
            const totalDays = new Date(currentYear, currentMonth + 1, 0).getDate();

            // Agregar días vacíos al principio del mes para alinear con el día correcto de la semana
            for (let i = 0; i < firstDayIndex; i++) {
                const emptyDiv = document.createElement('div');
                emptyDiv.className = 'calendar-day empty';
                calendarDaysGrid.appendChild(emptyDiv);
            }

            // Obtener la fecha de hoy
            const today = new Date();
            // Obtener la lista de parciales programados
            const parciales = getScheduledParciales();

            // Renderizar los días del mes
            for (let day = 1; day <= totalDays; day++) {
                const dayDiv = document.createElement('div');
                dayDiv.className = 'calendar-day';
                dayDiv.textContent = day;

                // Comprobar si es hoy
                if (currentYear === today.getFullYear() && currentMonth === today.getMonth() && day === today.getDate()) {
                    dayDiv.classList.add('today');
                }

                // Comprobar si hay algún parcial programado en este día
                const examsOnThisDay = parciales.filter(p => {
                    const examDate = new Date(p.fechaIso);
                    return examDate.getFullYear() === currentYear &&
                           examDate.getMonth() === currentMonth &&
                           examDate.getDate() === day;
                });

                if (examsOnThisDay.length > 0) {
                    dayDiv.classList.add('has-exam');
                    const dot = document.createElement('div');
                    dot.className = 'calendar-day-dot';
                    dayDiv.appendChild(dot);

                    // Tooltip con los parciales programados
                    const titles = examsOnThisDay.map(e => `${e.materia}: ${e.nombre}`).join('\n');
                    dayDiv.title = titles;
                }

                // Al hacer clic en un día del calendario, abrir modal y pre-cargar esa fecha
                dayDiv.addEventListener('click', () => {
                    openAddParcialModalWithDate(currentYear, currentMonth, day);
                });

                calendarDaysGrid.appendChild(dayDiv);
            }
        }

        // Navegación del calendario
        function prevMonth() {
            currentMonth--;
            if (currentMonth < 0) {
                currentMonth = 11;
                currentYear--;
            }
            renderCalendar();
        }

        function nextMonth() {
            currentMonth++;
            if (currentMonth > 11) {
                currentMonth = 0;
                currentYear++;
            }
            renderCalendar();
        }

        // Cambiar dinámicamente el título y botón del modal entre Crear y Editar
        function setModalMode(isEdit) {
            const modal = document.getElementById('addParcialModal');
            if (!modal) return;
            const titleEl = modal.querySelector('.modal-title');
            const submitBtn = modal.querySelector('.btn-form-submit');
            
            if (isEdit) {
                titleEl.innerHTML = `<i class="fa-solid fa-calendar-check"></i> Editar Examen Parcial`;
                submitBtn.innerHTML = `<i class="fa-solid fa-circle-check"></i> Guardar Cambios`;
            } else {
                titleEl.innerHTML = `<i class="fa-solid fa-calendar-plus"></i> Programar Nuevo Parcial`;
                submitBtn.innerHTML = `<i class="fa-solid fa-circle-check"></i> Guardar Examen`;
            }
        }

        // Abrir y cerrar el Modal
        function openAddParcialModal() {
            const modal = document.getElementById('addParcialModal');
            if (modal) {
                editingParcialId = null;
                setModalMode(false);
                modal.classList.add('show');
                // Poner la fecha de hoy por defecto en el selector
                const now = new Date();
                const offset = now.getTimezoneOffset() * 60000;
                const localISOTime = (new Date(now - offset)).toISOString().slice(0, 16);
                document.getElementById('parcialFecha').value = localISOTime;

                // Limpiar el buscador y restaurar la lista completa de materias al abrir
                const searchInput = document.getElementById('parcialMateriaSearch');
                if (searchInput) {
                    searchInput.value = '';
                }
                filterMateriaOptions();
            }
        }

        function openAddParcialModalWithDate(year, month, day) {
            const modal = document.getElementById('addParcialModal');
            if (modal) {
                editingParcialId = null;
                setModalMode(false);
                modal.classList.add('show');
                // Formatear la fecha seleccionada para el input datetime-local
                const pad = (n) => n.toString().padStart(2, '0');
                const now = new Date();
                // Usar hora actual para que no sea a las 00:00 obligatoriamente
                const hours = pad(now.getHours());
                const minutes = pad(now.getMinutes());
                const dateStr = `${year}-${pad(month + 1)}-${pad(day)}T${hours}:${minutes}`;
                document.getElementById('parcialFecha').value = dateStr;

                // Limpiar el buscador y restaurar la lista completa de materias al abrir
                const searchInput = document.getElementById('parcialMateriaSearch');
                if (searchInput) {
                    searchInput.value = '';
                }
                filterMateriaOptions();
            }
        }

        function openEditParcialModal(parcialId) {
            const card = document.querySelector(`.parcial-card[data-parcial-id="${parcialId}"]`);
            if (!card) return;

            editingParcialId = parcialId;
            setModalMode(true);

            // Leer datos cargados en el dataset de la tarjeta
            const materiaId = card.getAttribute('data-materia-id');
            const nombre = card.getAttribute('data-nombre');
            const fechaIso = card.getAttribute('data-fecha-iso');
            const descripcion = card.getAttribute('data-descripcion');

            // Pre-cargar en inputs
            document.getElementById('parcialMateria').value = materiaId;
            document.getElementById('parcialNombre').value = nombre;
            
            // Recortar 'YYYY-MM-DDTHH:MM:SS' a 'YYYY-MM-DDTHH:MM'
            if (fechaIso) {
                document.getElementById('parcialFecha').value = fechaIso.substring(0, 16);
            }
            
            document.getElementById('parcialDescripcion').value = descripcion || '';

            // Limpiar buscador y re-filtrar
            const searchInput = document.getElementById('parcialMateriaSearch');
            if (searchInput) {
                searchInput.value = '';
            }
            filterMateriaOptions();

            // Abrir modal
            const modal = document.getElementById('addParcialModal');
            if (modal) {
                modal.classList.add('show');
            }
        }

        function closeAddParcialModal() {
            const modal = document.getElementById('addParcialModal');
            if (modal) {
                editingParcialId = null;
                modal.classList.remove('show');
                document.getElementById('addParcialForm').reset();

                // Limpiar el buscador y restaurar la lista completa de materias al cerrar
                const searchInput = document.getElementById('parcialMateriaSearch');
                if (searchInput) {
                    searchInput.value = '';
                }
                filterMateriaOptions();
            }
        }

        function closeAddParcialModalOnOverlay(event) {
            if (event.target === event.currentTarget) {
                closeAddParcialModal();
            }
        }

        // Filtrar dinámicamente las materias en el dropdown de programación de parciales
        function filterMateriaOptions() {
            const searchInput = document.getElementById('parcialMateriaSearch');
            const select = document.getElementById('parcialMateria');
            if (!searchInput || !select) return;

            const cleanStr = str => str.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
            const query = cleanStr(searchInput.value);

            // Filtrar las opciones
            const filtered = allMateriaOptions.filter(opt => {
                if (opt.value === "") return true; // Mantener la opción por defecto
                return cleanStr(opt.text).includes(query);
            });

            // Guardar el valor seleccionado actualmente para ver si sigue disponible
            const prevSelectedVal = select.value;

            // Re-renderizar las opciones
            select.innerHTML = '';
            filtered.forEach(opt => {
                const optionEl = document.createElement('option');
                optionEl.value = opt.value;
                optionEl.textContent = opt.text;
                optionEl.disabled = opt.disabled;
                optionEl.selected = opt.selected;
                select.appendChild(optionEl);
            });

            // Intentar restaurar el valor seleccionado previamente si está en el conjunto filtrado
            const stillExists = filtered.some(opt => opt.value === prevSelectedVal);
            if (stillExists) {
                select.value = prevSelectedVal;
            } else {
                // Si no existe, dejar la opción vacía seleccionada
                select.value = "";
            }
        }

        // Enviar Formulario AJAX para Añadir o Editar Parcial
        async function submitParcialForm(event) {
            event.preventDefault();
            const materiaId = document.getElementById('parcialMateria').value;
            const nombre = document.getElementById('parcialNombre').value;
            const fecha = document.getElementById('parcialFecha').value;
            const descripcion = document.getElementById('parcialDescripcion').value;

            if (!materiaId || !nombre || !fecha) {
                showToast("Por favor, completa todos los campos requeridos.", true);
                return;
            }

            const url = editingParcialId ? "/edit-parcial" : "/add-parcial";
            const payload = {
                materia_id: materiaId,
                nombre: nombre,
                fecha: fecha,
                descripcion: descripcion
            };
            if (editingParcialId) {
                payload.parcial_id = editingParcialId;
            }

            try {
                const response = await fetch(url, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                const result = await response.json();
                if (result.success) {
                    showToast(editingParcialId ? "¡Parcial actualizado con éxito!" : "¡Parcial programado con éxito!");
                    closeAddParcialModal();
                    
                    // Esperar un instante y recargar para refrescar la lista y el calendario
                    setTimeout(() => {
                        location.reload();
                    }, 800);
                } else {
                    showToast("Error: " + result.message, true);
                }
            } catch (error) {
                console.error("Error al procesar parcial:", error);
                showToast("Error de conexión con el servidor", true);
            }
        }

        // Eliminar Parcial con Confirmación
        async function deleteParcial(parcialId) {
            if (!confirm("¿Estás seguro de que deseas eliminar este parcial de tu agenda?")) return;

            try {
                const response = await fetch("/delete-parcial", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ parcial_id: parcialId })
                });

                const result = await response.json();
                if (result.success) {
                    showToast("Parcial eliminado correctamente.");
                    
                    // Quitar del DOM con una transición elegante
                    const card = document.querySelector(`.parcial-card[data-parcial-id="${parcialId}"]`);
                    if (card) {
                        card.style.opacity = '0';
                        card.style.transform = 'scale(0.9)';
                        setTimeout(() => {
                            card.remove();
                            // Si ya no quedan parciales, mostrar empty state
                            const container = document.getElementById('parcialesCardsContainer');
                            if (container && container.querySelectorAll('.parcial-card').length === 0) {
                                container.innerHTML = `
                                    <div class="empty-state" id="emptyParcialesState">
                                        <i class="fa-solid fa-calendar-check" style="color: rgba(139, 92, 246, 0.2);"></i>
                                        <p>No tienes parciales programados.</p>
                                        <p style="font-size: 0.85rem; color: var(--text-secondary);">
                                            Haz clic en "Añadir Parcial" para organizar tu agenda de exámenes.
                                        </p>
                                    </div>
                                `;
                            }
                            renderCalendar();
                        }, 300);
                    }
                } else {
                    showToast("Error: " + result.message, true);
                }
            } catch (error) {
                console.error("Error al eliminar parcial:", error);
                showToast("Error de conexión con el servidor", true);
            }
        }

        // Inicializar y correr cuentas regresivas segundo a segundo
        function updateCountdowns() {
            const cards = document.querySelectorAll('.parcial-card');
            const now = new Date().getTime();

            cards.forEach(card => {
                const id = card.getAttribute('data-parcial-id');
                const fechaIso = card.getAttribute('data-fecha-iso');
                const timerSpan = document.getElementById(`countdown-${id}`);
                if (!timerSpan || !fechaIso) return;

                const examTime = new Date(fechaIso).getTime();
                const difference = examTime - now;

                if (difference <= 0) {
                    // Si ya pasó, comprobar si fue hoy o hace poco
                    const hoursPast = Math.abs(difference) / (1000 * 60 * 60);
                    if (hoursPast < 12) {
                        timerSpan.textContent = "¡Hoy es el examen! 📝";
                        timerSpan.className = "countdown-time today";
                    } else {
                        timerSpan.textContent = "Finalizado";
                        timerSpan.className = "countdown-time finished";
                    }
                } else {
                    // Calcular días, horas, minutos y segundos restantes
                    const days = Math.floor(difference / (1000 * 60 * 60 * 24));
                    const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((difference % (1000 * 60)) / 1000);

                    let timeString = "";
                    if (days > 0) timeString += `${days}d `;
                    timeString += `${hours.toString().padStart(2, '0')}h `;
                    timeString += `${minutes.toString().padStart(2, '0')}m `;
                    timeString += `${seconds.toString().padStart(2, '0')}s`;

                    timerSpan.textContent = timeString;

                    // Estilo urgente si queda menos de 24 horas
                    if (days === 0) {
                        timerSpan.className = "countdown-time urgent";
                    } else {
                        timerSpan.className = "countdown-time";
                    }
                }
            });
        }

        // ==========================================
        // FUNCIONES PARA HORARIOS DE CURSADA
        // ==========================================

        // Filtrar materias en el modal de horario omitiendo tildes
        function filterHorarioMateriaOptions() {
            const searchInput = document.getElementById('horarioMateriaSearch');
            const select = document.getElementById('horarioMateria');
            if (!searchInput || !select) return;

            const cleanStr = str => str ? str.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim() : "";
            const query = cleanStr(searchInput.value);

            select.innerHTML = '';

            const filteredOptions = allHorarioMateriaOptions.filter(opt => {
                if (opt.value === "") return true;
                return cleanStr(opt.text).includes(query);
            });

            filteredOptions.forEach(opt => {
                const optionEl = document.createElement('option');
                optionEl.value = opt.value;
                optionEl.textContent = opt.text;
                optionEl.disabled = opt.disabled;
                optionEl.selected = opt.selected;
                select.appendChild(optionEl);
            });
        }

        function openAddHorarioModal(diaInicial = null) {
            editingHorarioId = null;
            document.getElementById('horarioModalTitle').innerHTML = '<i class="fa-solid fa-calendar-plus"></i> Registrar Horario de Cursada';
            document.getElementById('horarioSubmitBtn').innerHTML = '<i class="fa-solid fa-circle-check"></i> Guardar Horario';
            document.getElementById('horarioForm').reset();

            if (diaInicial) {
                document.getElementById('horarioDia').value = diaInicial;
            }

            const searchInput = document.getElementById('horarioMateriaSearch');
            if (searchInput) searchInput.value = '';
            filterHorarioMateriaOptions();

            const modal = document.getElementById('horarioModal');
            if (modal) {
                modal.classList.add('show');
            }
        }

        function openEditHorarioModal(horarioId) {
            const card = document.querySelector(`.horario-card[data-horario-id="${horarioId}"]`);
            if (!card) return;

            editingHorarioId = horarioId;
            const materiaId = card.getAttribute('data-materia-id');
            const dia = card.getAttribute('data-dia');
            const horaInicio = card.getAttribute('data-hora-inicio');
            const horaFin = card.getAttribute('data-hora-fin');
            const aula = card.getAttribute('data-aula');

            document.getElementById('horarioModalTitle').innerHTML = '<i class="fa-solid fa-pen-to-square"></i> Editar Horario de Cursada';
            document.getElementById('horarioSubmitBtn').innerHTML = '<i class="fa-solid fa-rotate"></i> Actualizar Horario';

            const searchInput = document.getElementById('horarioMateriaSearch');
            if (searchInput) searchInput.value = '';
            filterHorarioMateriaOptions();

            document.getElementById('horarioMateria').value = materiaId;
            document.getElementById('horarioDia').value = dia;
            document.getElementById('horarioInicio').value = horaInicio;
            document.getElementById('horarioFin').value = horaFin;
            document.getElementById('horarioAula').value = aula;

            const modal = document.getElementById('horarioModal');
            if (modal) {
                modal.classList.add('show');
            }
        }

        function closeHorarioModal() {
            const modal = document.getElementById('horarioModal');
            if (modal) {
                modal.classList.remove('show');
                editingHorarioId = null;
            }
        }

        function closeHorarioModalOnOverlay(event) {
            if (event.target === event.currentTarget) {
                closeHorarioModal();
            }
        }

        async function submitHorarioForm(event) {
            event.preventDefault();

            const materia_id = document.getElementById('horarioMateria').value;
            const dia_semana = document.getElementById('horarioDia').value;
            const hora_inicio = document.getElementById('horarioInicio').value;
            const hora_fin = document.getElementById('horarioFin').value;
            const aula_comision = document.getElementById('horarioAula').value;

            if (!materia_id) {
                showToast("Por favor selecciona una materia.", true);
                return;
            }

            if (hora_fin <= hora_inicio) {
                showToast("La hora de fin debe ser posterior a la hora de inicio.", true);
                return;
            }

            const isEdit = editingHorarioId !== null;
            const endpoint = isEdit ? '/edit-horario' : '/add-horario';
            const payload = {
                materia_id: parseInt(materia_id),
                dia_semana: parseInt(dia_semana),
                hora_inicio: hora_inicio,
                hora_fin: hora_fin,
                aula_comision: aula_comision
            };

            if (isEdit) {
                payload.horario_id = editingHorarioId;
            }

            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();
                if (data.success) {
                    showToast(data.message);
                    closeHorarioModal();
                    setTimeout(() => {
                        window.location.reload();
                    }, 400);
                } else {
                    showToast(data.message || "Error al procesar el horario.", true);
                }
            } catch (err) {
                showToast("Error de conexión con el servidor.", true);
            }
        }

        async function deleteHorario(horarioId) {
            if (!confirm("¿Estás seguro de que deseas eliminar este horario de cursada?")) {
                return;
            }

            try {
                const response = await fetch('/delete-horario', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ horario_id: horarioId })
                });

                const data = await response.json();
                if (data.success) {
                    showToast(data.message);
                    const card = document.querySelector(`.horario-card[data-horario-id="${horarioId}"]`);
                    if (card) {
                        card.style.opacity = '0';
                        card.style.transform = 'scale(0.9)';
                        setTimeout(() => {
                            window.location.reload();
                        }, 400);
                    } else {
                        window.location.reload();
                    }
                } else {
                    showToast(data.message || "Error al eliminar el horario.", true);
                }
            } catch (err) {
                showToast("Error de conexión al eliminar el horario.", true);
            }
        }

        // Mostrar Toast de notificación
        function showToast(message, isError = false) {
            const toast = document.getElementById("toast");
            const toastMessage = document.getElementById("toastMessage");
            const toastIcon = toast.querySelector("i");

            toastMessage.textContent = message;
            
            if (isError) {
                toastIcon.className = "fa-solid fa-triangle-exclamation";
                toastIcon.style.color = "#ef4444";
                toast.style.borderColor = "rgba(239, 68, 68, 0.4)";
            } else {
                toastIcon.className = "fa-solid fa-circle-check";
                toastIcon.style.color = "var(--color-aprobada)";
                toast.style.borderColor = "rgba(139, 92, 246, 0.3)";
            }

            toast.classList.add("show");

            setTimeout(() => {
                toast.classList.remove("show");
            }, 2500);
        }
    
