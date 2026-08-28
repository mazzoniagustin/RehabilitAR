(function() {
  let chartIngresosInstance = null;
  let chartActividadesInstance = null;
  let currentAuditData = null;

window.initAuditDashboard = async function() {
    const user = getUser(); 
    if (!user || user.rol !== 'ADMINISTRATIVO') return;

    const homePanel = document.getElementById('panelInicio');
    if (!homePanel) return;
    if (document.getElementById('adminAuditSection')) return;

    const currentDate = new Date();
    const currentYear = currentDate.getFullYear();

  let yearOptions = '<option value="" selected>Todos los años</option>';

  for (let year = 2026; year <= currentYear; year++) {
      yearOptions += `<option value="${year}">${year}</option>`;
  }

    let monthOptions = '<option value="" selected>Todos los meses</option>';
    const monthNames = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
    for (let i = 1; i <= 12; i++) {
        monthOptions += `<option value="${i}">${monthNames[i-1]}</option>`;
    }

    const auditContainer = document.createElement('div');
    auditContainer.id = 'adminAuditSection';
    auditContainer.style.cssText = 'margin-top: 32px; border-top: 2px solid var(--border); padding-top: 24px;';
    
    auditContainer.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 15px;">
        <div>
          <h3 style="font-family: 'DM Serif Display', serif; font-size: 1.6rem; color: var(--text);">🛡️ Registro de auditoría</h3>
          <p style="color: var(--muted); font-size: 0.9rem;">Métricas interactivas de ingresos y operaciones.</p>
        </div>
        
        <div style="display: flex; gap: 10px; align-items: center; background: white; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
          <select id="auditFilterYear" style="padding: 6px; border-radius: 4px; border: 1px solid var(--border);">
            ${yearOptions}
          </select>
          <select id="auditFilterMonth" style="padding: 6px; border-radius: 4px; border: 1px solid var(--border);">
            ${monthOptions}
          </select>
          <button class="btn btn-sm" id="btnRefreshGlobalAudit">Filtrar</button>
          <button class="btn btn-sm" id="btnExportAudit">Exportar</button>
          
        </div>
      </div>

      <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 24px;">
        <div style="flex: 2; min-width: 300px; background: white; padding: 20px; border-radius: 8px; border: 1px solid var(--border);">
          <h4 style="margin-bottom: 15px; color: var(--text);">📈 Histórico de Recaudación</h4>
          <div style="position: relative; height: 250px;">
            <canvas id="chartIngresos"></canvas>
          </div>
        </div>

        <div style="flex: 1; min-width: 280px; background: white; padding: 20px; border-radius: 8px; border: 1px solid var(--border);">
          <h4 style="margin-bottom: 15px; color: var(--text);">🎯 Reservas por Actividad</h4>
          <div style="position: relative; height: 250px; display: flex; justify-content: center;">
            <canvas id="chartActividades"></canvas>
          </div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 24px;">
        <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid var(--border);">
          <h4 style="margin-bottom: 15px; color: var(--text);">💰 Total Recaudado</h4>
          <h2 id="auditDisplayTotalRevenue" style="color: #2ecc71; margin-bottom: 15px; font-size: 2rem;">$0</h2>
          
          <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #edf2f7;">
            <span style="color: var(--muted);">Suscripciones</span><strong id="auditRevSub">$0</strong>
          </div>
          <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #edf2f7;">
            <span style="color: var(--muted);">Reservas</span><strong id="auditRevRes">$0</strong>
          </div>
          <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #edf2f7;">
            <span style="color: var(--muted);">Pago de Deudas</span><strong id="auditRevDebt">$0</strong>
          </div>
        </div>

        <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid var(--border);">
          <h4 style="margin-bottom: 15px; color: var(--text);">🛡️ Últimas Suspensiones</h4>
          <div style="max-height: 180px; overflow-y: auto; font-size: 0.85rem;">
            <ul id="auditTraceabilityList" style="list-style: none; padding: 0; color: var(--muted);"></ul>
          </div>
        </div>
      </div>

      <div class="section-card" style="background: white; padding: 20px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 24px;">
        <h4 style="margin-bottom: 8px;">🔍 Auditar Usuario</h4>
        <p style="color: var(--muted); font-size: 0.85rem;">Inspeccioná la información relevante según el rol: créditos e inasistencias para clientes, clases dictadas para profesores, etc.</p>
        
        <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 12px;">
          <label for="auditUserSelect" style="font-size: 0.85rem; color: var(--text); font-weight: 500;">Seleccionar Usuario (Abonados, No Abonados o Profesores):</label>
          <select id="auditUserSelect" style="padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 0.9rem; background: white;">
            <option value="">Cargando lista de usuarios...</option>
          </select>
        </div>

        <div id="userAuditResults" style="display: none; background: #f7fafc; padding: 16px; border-radius: 6px; border-left: 4px solid var(--teal); margin-top: 20px;">
          <div id="userAuditStatsGrid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; margin-bottom: 16px;"></div>

          <h6 style="font-size: 0.9rem; margin-bottom: 6px; color: #2d3748;">Historial de Motivos de Suspensión:</h6>
          <ul id="userAuditLog" style="padding-left: 20px; font-size: 0.85rem; color: #4a5568; line-height: 1.5;"></ul>
        </div>
      </div>
    `;

    homePanel.appendChild(auditContainer);
    

    document.getElementById('btnRefreshGlobalAudit').onclick = fetchGlobalExtendedStats;
    document.getElementById('auditUserSelect').onchange = fetchUserStats;
    document.getElementById('btnExportAudit').onclick = exportAuditExcel;

    fetchGlobalExtendedStats();
    populateUsersFilter();
  };

  async function fetchGlobalExtendedStats() {
    try {
      const year = document.getElementById('auditFilterYear').value;
      const month = document.getElementById('auditFilterMonth').value;

      const params = new URLSearchParams();
      if (year) params.set('year', year);
      if (month) params.set('month', month);
      const qs = params.toString();
      const url = `${API}/audit/global-stats${qs ? `?${qs}` : ''}`;
      
      const res = await fetch(url, { headers: authH() });
      if (!res.ok) {
        const errorBody = await res.text().catch(() => '');
        console.error(`Error al filtrar auditoría (${res.status}):`, errorBody);
        alert(`No se pudo aplicar el filtro (error ${res.status}). Revisá la consola para más detalle.`);
        return;
      }

      const data = await res.json();
      currentAuditData = data;
      
      const fin = data.financials;
      const ops = data.operations;

      document.getElementById('auditDisplayTotalRevenue').textContent = `$${fin.totalRevenue.toLocaleString('es-AR')}`;
      document.getElementById('auditRevSub').textContent = `$${fin.breakdown.SUBSCRIPTION.toLocaleString('es-AR')}`;
      document.getElementById('auditRevRes').textContent = `$${fin.breakdown.RESERVATION.toLocaleString('es-AR')}`;
      document.getElementById('auditRevDebt').textContent = `$${fin.breakdown.DEBT.toLocaleString('es-AR')}`;

      const traceList = document.getElementById('auditTraceabilityList');
      traceList.innerHTML = '';
      if (data.traceability.length === 0) {
        traceList.innerHTML = '<li>Sin registros recientes.</li>';
      } else {
        data.traceability.forEach(log => {
          const d = new Date(log.date).toLocaleDateString('es-AR', {day: '2-digit', month:'2-digit'});
          traceList.innerHTML += `<li style="border-bottom: 1px solid #eee; padding: 6px 0;">📅 <strong>${d}</strong> | Admin: ${log.actor} suspendió a ${log.target} ("${log.reason}")</li>`;
        });
      }

      const ctxIngresos = document.getElementById('chartIngresos').getContext('2d');
      if (chartIngresosInstance) chartIngresosInstance.destroy();
      
      let labelsIngresos = fin.chartLabels;
      let datosIngresos = fin.chartData;
      if (datosIngresos.every(val => val === 0)) {
          labelsIngresos = ['Sin pagos registrados'];
      }

      chartIngresosInstance = new Chart(ctxIngresos, {
        type: 'bar',
        data: {
          labels: labelsIngresos,
          datasets: [{
            label: 'Recaudación Total ($)',
            data: datosIngresos,
            backgroundColor: '#319795', 
            borderRadius: 4
          }]
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true, suggestedMax: 10 } }
        }
      });
   
      const ctxActividades = document.getElementById('chartActividades').getContext('2d');
      if (chartActividadesInstance) chartActividadesInstance.destroy();
      
      let datosActividades = [ops.activities.TREN_SUPERIOR, ops.activities.TREN_MEDIO, ops.activities.TREN_INFERIOR];
      let labelsActividades = ['T. Superior', 'T. Medio', 'T. Inferior'];
      let coloresActividades = ['#4c51bf', '#ed8936', '#48bb78'];
    
      if (datosActividades.every(val => val === 0)) {
          datosActividades = [1]; 
          labelsActividades = ['Sin Reservas'];
          coloresActividades = ['#e2e8f0']; 
      }

      chartActividadesInstance = new Chart(ctxActividades, {
        type: 'doughnut',
        data: {
          labels: labelsActividades,
          datasets: [{
            data: datosActividades,
            backgroundColor: coloresActividades,
            borderWidth: 2,
            borderColor: '#ffffff'
          }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });

    } catch (err) {
      console.error("Error obteniendo auditoría global:", err);
    }
  }


  const ROL_LABELS_AUDIT = {
    ABONADO: 'Abonado',
    NO_ABONADO: 'No abonado',
    PROFESOR: 'Profesor',
  };

  async function populateUsersFilter() {
    try {
      const res = await fetch(`${API}/staff/users`, { headers: authH() });
      if (!res.ok) return;
      const users = await res.json();

      const userSelect = document.getElementById('auditUserSelect');
      userSelect.innerHTML = '<option value="">-- Seleccionar un usuario para auditar --</option>';


      const auditables = users.filter(u =>
        ['ABONADO', 'NO_ABONADO', 'PROFESOR'].includes(u.rol)
      );

      if (auditables.length === 0) {
        userSelect.innerHTML = '<option value="">No hay usuarios para auditar</option>';
        return;
      }

      auditables.sort((a, b) => `${a.name} ${a.surname}`.localeCompare(`${b.name} ${b.surname}`));

      auditables.forEach(u => {
        const fullName = `${u.name || ''} ${u.surname || ''} (${ROL_LABELS_AUDIT[u.rol] || u.rol})`;
        userSelect.innerHTML += `<option value="${u.id}">${fullName}</option>`;
      });

    } catch (err) {
      console.error("Error al poblar el buscador de usuarios:", err);
      document.getElementById('auditUserSelect').innerHTML = '<option value="">Error cargando la lista</option>';
    }
  }

  const AUDIT_USER_STAT_MAPS = {
    ABONADO: [
      { label: 'CRÉDITOS USADOS', key: 'usedCredits', color: '#2d3748' },
      { label: 'SUSPENSIONES', key: 'totalSuspensions', color: '#e53e3e' },
      { label: 'INASISTENCIAS', key: 'absenceCount', color: '#dd6b20' },
      { label: 'CANCELACIONES', key: 'cancellationCount', color: '#805ad5' },
      { label: 'DEUDA ACTUAL', key: 'financials.totalDebt', color: '#e74c3c', money: true },
    ],
    NO_ABONADO: [
      { label: 'CRÉDITOS USADOS', key: 'usedCredits', color: '#2d3748' },
      { label: 'SUSPENSIONES', key: 'totalSuspensions', color: '#e53e3e' },
      { label: 'INASISTENCIAS', key: 'absenceCount', color: '#dd6b20' },
      { label: 'CANCELACIONES', key: 'cancellationCount', color: '#805ad5' },
      { label: 'DEUDA ACTUAL', key: 'financials.totalDebt', color: '#e74c3c', money: true },
    ],
    PROFESOR: [
      { label: 'CLASES DICTADAS', key: 'totalClasses', color: '#2d3748' },
      { label: 'SUSPENSIONES', key: 'totalSuspensions', color: '#e53e3e' },
    ],
  };

  function _leerValorAnidado(obj, path) {
    return path.split('.').reduce((acc, k) => (acc ? acc[k] : undefined), obj);
  }

  async function fetchUserStats() {
    const userId = document.getElementById('auditUserSelect').value;
    const resultsContainer = document.getElementById('userAuditResults');

    if (!userId) {
        resultsContainer.style.display = 'none';
        return;
    }

    try {
      const res = await fetch(`${API}/audit/user-stats/${userId}`, { headers: authH() });
      const data = await res.json();
      
      if (!res.ok) {
        alert(data.detail || "No se pudo completar la auditoría del usuario.");
        return;
      }

      resultsContainer.style.display = 'block';

      const statMap = AUDIT_USER_STAT_MAPS[data.rol] || [];
      document.getElementById('userAuditStatsGrid').innerHTML = statMap.map(s => {
        const raw = _leerValorAnidado(data, s.key);
        const value = s.money
          ? `$${Number(raw || 0).toLocaleString('es-AR', { minimumFractionDigits: 2 })}`
          : (raw ?? 0);
        return `
          <div style="background: white; padding: 10px; border-radius: 4px; border: 1px solid #e2e8f0;">
            <span style="font-size: 0.75rem; color: #718096; display: block;">${s.label}</span>
            <strong style="font-size: 1.25rem; color: ${s.color};">${value}</strong>
          </div>`;
      }).join('') || '<p style="color:#718096;font-size:0.85rem;">Sin métricas para este rol.</p>';

      const logList = document.getElementById('userAuditLog');
      logList.innerHTML = '';
      
      if (!data.suspensionHistory || data.suspensionHistory.length === 0) {
        logList.innerHTML = '<li style="list-style: none; color: #718096;">El usuario no registra entradas de suspensión en el sistema.</li>';
      } else {
        data.suspensionHistory.forEach(item => {
          const date = new Date(item.createdAt).toLocaleDateString('es-AR', {
            day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
          });
          logList.innerHTML += `<li>📅 <strong>${date}</strong> — Motivo: <span style="color: #c53030;">"${item.reason}"</span></li>`;
        });
      }
    } catch (err) {
      console.error("Error al procesar la auditoría del usuario:", err);
    }
  }

 function exportAuditExcel() {

    if (!currentAuditData) {
        alert('Primero cargá la auditoría.');
        return;
    }

    const fin = currentAuditData.financials;
    const ops = currentAuditData.operations;

    const year =
        document.getElementById('auditFilterYear').value || 'Todos los años';

    const monthSelect = document.getElementById('auditFilterMonth');
    const month =
        monthSelect.value === ""
            ? "Todos los meses"
            : monthSelect.options[monthSelect.selectedIndex].text;

    const record = currentAuditData.traceability.map(t => ({
        Fecha: new Date(t.date).toLocaleString('es-AR'),
        Administrador: t.actor,
        Usuario: t.target,
        Motivo: t.reason
    }));


    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet([]);


    XLSX.utils.sheet_add_aoa(ws, [
        ['REPORTE DE AUDITORÍA']
    ], { origin: "A1" });


    XLSX.utils.sheet_add_aoa(ws, [
        ['Fecha de exportación', new Date().toLocaleString('es-AR')],
        ['Año', year],
        ['Mes', month]
    ], { origin: "A3" });


    XLSX.utils.sheet_add_aoa(ws, [
        [],
        ['RESUMEN GENERAL'],
        ['Concepto', 'Valor'],
        ['Total recaudado', `$${fin.totalRevenue.toLocaleString('es-AR')}`],
        ['Suscripciones', `$${fin.breakdown.SUBSCRIPTION.toLocaleString('es-AR')}`],
        ['Reservas', `$${fin.breakdown.RESERVATION.toLocaleString('es-AR')}`],
        ['Pago de deudas', `$${fin.breakdown.DEBT.toLocaleString('es-AR')}`],
        ['Reservas Tren Superior', `${ops.activities.TREN_SUPERIOR}`],
        ['Reservas Tren Medio', `${ops.activities.TREN_MEDIO}`],
        ['Reservas Tren Inferior', `${ops.activities.TREN_INFERIOR}`]
    ], { origin: "A7" });


    let fila = 18;

    XLSX.utils.sheet_add_aoa(ws, [
        ['HISTORIAL DE SUSPENSIONES'],
        ['Fecha', 'Administrador', 'Usuario', 'Motivo']
    ], {
        origin: `A${fila}`
    });

    fila += 2;

    if (record.length === 0) {

        XLSX.utils.sheet_add_aoa(ws, [
            ['No existen suspensiones para el filtro seleccionado.']
        ], {
            origin: `A${fila}`
        });

    } else {

        record.forEach(r => {

            XLSX.utils.sheet_add_aoa(ws, [[
                r.Fecha,
                r.Administrador,
                r.Usuario,
                r.Motivo
            ]], {
                origin: `A${fila}`
            });

            fila++;

        });

    }


    ws["!cols"] = [
        { wch: 24 }, 
        { wch: 28 }, 
        { wch: 28 }, 
        { wch: 55 }  
    ];

    XLSX.utils.book_append_sheet(wb, ws, "Auditoría");


    XLSX.writeFile(
        wb,
        `Auditoria_${year.replace(/\s/g, "_")}_${month.replace(/\s/g, "_")}.xlsx`
    );
  }
})();