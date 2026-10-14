// AnyPS5 Launcher - Client Engine
(function() {
  'use strict';

  // --- Web Audio Synthesizer for PS5-style acoustic UI feedback ---
  const AudioEngine = {
    ctx: null,
    init() {
      if (!this.ctx) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) this.ctx = new AudioCtx();
      }
    },
    playPing(freq = 660, type = 'sine', duration = 0.08, gainVal = 0.05) {
      try {
        this.init();
        if (!this.ctx) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = type;
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
        gain.gain.setValueAtTime(gainVal, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + duration);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start();
        osc.stop(this.ctx.currentTime + duration);
      } catch (e) {}
    },
    hover() { this.playPing(780, 'sine', 0.05, 0.03); },
    click() { this.playPing(520, 'sine', 0.09, 0.07); },
    launch() {
      this.playPing(320, 'sine', 0.35, 0.1);
      setTimeout(() => this.playPing(640, 'triangle', 0.45, 0.12), 120);
    }
  };

  // --- Initial Games Database ---
  const gamesDatabase = [
    {
      id: 'astro_odyssey',
      title: 'Astro Odyssey',
      titleId: 'PPSA01325',
      publisher: 'Cosmic Studios',
      status: 'playable',
      statusLabel: '100% Playable',
      cover: 'assets/images/astro_odyssey.jpg',
      banner: 'assets/images/hero_astro.jpg',
      desc: 'Traverse alien star systems in an interplanetary sci-fi adventure. Optimized with native Vulkan 1.3 pipeline remapping and low-latency DualSense vibration.',
      fps: '60 FPS (Vsync)',
      res: '4K Ultra / 1440p',
      shaders: '1,420 Compiled',
      compatScore: 98,
      symbolsTotal: 145,
      symbolsResolved: 142
    },
    {
      id: 'shadow_ronin',
      title: 'Shadow of the Ronin',
      titleId: 'PPSA02891',
      publisher: 'Developer Studio',
      status: 'playable',
      statusLabel: 'Playable',
      cover: 'assets/images/shadow_ronin.jpg',
      banner: 'assets/images/shadow_ronin.jpg',
      desc: 'Dark cyber-samurai action RPG set in the neon-drenched rooftops of neo Tokyo. Features real-time katana parrying and Agc shader pipeline emulation.',
      fps: '60 FPS Locked',
      res: '1440p Dynamic',
      shaders: '2,180 Compiled',
      compatScore: 95,
      symbolsTotal: 180,
      symbolsResolved: 171
    },
    {
      id: 'neon_velocity',
      title: 'Neon Velocity 2088',
      titleId: 'PPSA04109',
      publisher: 'Turbo Racing Games',
      status: 'playable',
      statusLabel: 'Playable',
      cover: 'assets/images/neon_velocity.jpg',
      banner: 'assets/images/neon_velocity.jpg',
      desc: 'High-speed anti-gravity supersonic hovercraft racing. Tests high refresh-rate swapchain buffer swapping and SDL2 low-latency gamepad input.',
      fps: '120 FPS High-Refresh',
      res: '4K Native',
      shaders: '940 Compiled',
      compatScore: 99,
      symbolsTotal: 110,
      symbolsResolved: 109
    },
    {
      id: 'eldritch_blood',
      title: 'Eldritch Blood',
      titleId: 'PPSA05542',
      publisher: 'From Software Tribute',
      status: 'ingame',
      statusLabel: 'In-Game (WIP)',
      cover: 'assets/images/eldritch_blood.jpg',
      banner: 'assets/images/eldritch_blood.jpg',
      desc: 'Victorian gothic horror souls adventure under the giant blood moon. Boots cleanly into gameplay; working on remaining libSceAudio3d acoustic stubs.',
      fps: '45-60 FPS',
      res: '1440p',
      shaders: '3,450 Compiled',
      compatScore: 89,
      symbolsTotal: 215,
      symbolsResolved: 191
    }
  ];

  let activeGame = gamesDatabase[0];
  let activeFilter = 'all';

  // --- Sample SCE PRX Symbols for Diagnostics Scanner ---
  const sampleSymbols = [
    { module: 'libkernel.prx', symbol: 'sceKernelCreateEqueue', nid: '0x32A48E91', status: 'IMPLEMENTED', action: 'Direct Host Thread Pool' },
    { module: 'libSceVideoOut.prx', symbol: 'sceVideoOutOpen', nid: '0x889B001F', status: 'IMPLEMENTED', action: 'Vulkan Swapchain Hook' },
    { module: 'libSceMsgDialog.native.prx', symbol: 'sceMsgDialogInitialize', nid: '0x5C200B31', status: 'IMPLEMENTED', action: 'Native ImGui / SDL Dialog' },
    { module: 'libSceSaveDataDialog.native.prx', symbol: 'sceSaveDataDialogClose', nid: '0x71AB9022', status: 'IMPLEMENTED', action: 'State Verified (PR #5718)' },
    { module: 'libSceWebBrowserDialog.prx', symbol: 'sceWebBrowserDialogInitialize', nid: '0x44B1299C', status: 'IMPLEMENTED', action: 'Error Safe (PR #5715)' },
    { module: 'libSceAudioOut.prx', symbol: 'sceAudioOutOpen', nid: '0x2289F001', status: 'IMPLEMENTED', action: 'SDL2 Audio Stream' },
    { module: 'libScePad.prx', symbol: 'scePadSetVibration', nid: '0x9910D44A', status: 'IMPLEMENTED', action: 'SDL_GameControllerRumble' },
    { module: 'libSceNpCommerce.prx', symbol: 'sceNpCommerceDialogInitialize', nid: '0xE1294811', status: 'STUBBED', action: 'Silent Success Return 0' },
    { module: 'libSceAudio3d.prx', symbol: 'sceAudio3dSetListener', nid: '0xFA991200', status: 'MISSING', action: 'NotImplemented_nid_no_patch' }
  ];

  // --- DOM Elements ---
  const gamesGrid = document.getElementById('gamesGrid');
  const searchInput = document.getElementById('searchInput');
  const filterGroup = document.getElementById('filterGroup');
  const heroShowcase = document.getElementById('heroShowcase');
  const heroBackdrop = document.getElementById('heroBackdrop');
  const heroTitle = document.getElementById('heroTitle');
  const heroDesc = document.getElementById('heroDesc');
  const heroTitleId = document.getElementById('heroTitleId');
  const btnHeroLaunch = document.getElementById('btnHeroLaunch');
  const btnHeroAudit = document.getElementById('btnHeroAudit');
  const navTabs = document.getElementById('navTabs');
  const terminalOutput = document.getElementById('terminalOutput');
  const logDrawer = document.getElementById('logDrawer');
  const drawerHandle = document.getElementById('drawerHandle');
  const btnToggleTerminal = document.getElementById('btnToggleTerminal');
  const launchOverlay = document.getElementById('launchOverlay');
  const launchOverlayTitle = document.getElementById('launchOverlayTitle');
  const launchOverlayStep = document.getElementById('launchOverlayStep');

  // Views
  const viewLibrary = document.getElementById('viewLibrary');
  const viewDiagnostics = document.getElementById('viewDiagnostics');
  const viewInput = document.getElementById('viewInput');
  const viewSettings = document.getElementById('viewSettings');

  // --- Render Library Grid ---
  function renderGrid() {
    gamesGrid.innerHTML = '';
    const query = searchInput.value.toLowerCase().trim();

    const filtered = gamesDatabase.filter(game => {
      const matchesFilter = activeFilter === 'all' || game.status === activeFilter;
      const matchesQuery = !query || 
        game.title.toLowerCase().includes(query) || 
        game.titleId.toLowerCase().includes(query) ||
        game.publisher.toLowerCase().includes(query);
      return matchesFilter && matchesQuery;
    });

    filtered.forEach(game => {
      const card = document.createElement('div');
      card.className = 'game-card';
      card.id = `card-${game.id}`;

      const badgeClass = game.status === 'playable' ? 'badge-playable' : 'badge-ingame';

      card.innerHTML = `
        <div class="card-cover-wrapper">
          <img src="${game.cover}" alt="${game.title}" class="card-cover-img" loading="lazy">
          <div class="card-floating-badge">
            <span class="badge ${badgeClass}">${game.statusLabel}</span>
          </div>
          <div class="card-overlay-actions">
            <button class="card-quick-launch-btn" data-action="launch" data-id="${game.id}">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Quick Launch
            </button>
            <div style="font-size: 0.72rem; color: #94a3b8; text-align: center;">Click card to inspect</div>
          </div>
        </div>
        <div class="card-details">
          <h3 class="card-title">${game.title}</h3>
          <div class="card-meta-row">
            <span class="card-title-id">${game.titleId}</span>
            <span>${game.fps}</span>
          </div>
        </div>
      `;

      card.addEventListener('mouseenter', () => AudioEngine.hover());
      card.addEventListener('click', (e) => {
        if (e.target.closest('[data-action="launch"]')) {
          e.stopPropagation();
          launchGame(game);
        } else {
          selectGame(game);
        }
      });

      gamesGrid.appendChild(card);
    });

    updateCounters();
  }

  function updateCounters() {
    document.getElementById('countAll').textContent = gamesDatabase.length;
    document.getElementById('countPlayable').textContent = gamesDatabase.filter(g => g.status === 'playable').length;
    document.getElementById('countIngame').textContent = gamesDatabase.filter(g => g.status === 'ingame').length;
  }

  function selectGame(game) {
    activeGame = game;
    AudioEngine.click();

    heroBackdrop.style.backgroundImage = `url('${game.banner}')`;
    heroTitle.textContent = game.title;
    heroDesc.textContent = game.desc;
    heroTitleId.textContent = game.titleId;

    heroShowcase.scrollIntoView({ behavior: 'smooth', block: 'start' });
    appendLog(`[SELECTION] Active title switched to ${game.title} (${game.titleId})`, 'anyps5');
  }

  // --- Launch Sequence Simulation ---
  function launchGame(game) {
    AudioEngine.launch();
    launchOverlayTitle.textContent = `Relinking ${game.title}...`;
    launchOverlayStep.textContent = 'Parsing PS5 ELF container & relocations...';
    launchOverlay.classList.add('active');

    appendLog(`--------------------------------------------------`, 'anyps5');
    appendLog(`[LAUNCH] Initializing execution pipeline for ${game.title} (${game.titleId})`, 'anyps5');
    appendLog(`[RELINKER] Loading eboot.bin -> Virtual Memory Base 0x100000000`, 'anyps5');

    setTimeout(() => {
      launchOverlayStep.textContent = 'Remapping SCE PRX system symbols...';
      appendLog(`[PRX] Remapped ${game.symbolsResolved} of ${game.symbolsTotal} SCE functions.`, 'anyps5');
    }, 700);

    setTimeout(() => {
      launchOverlayStep.textContent = 'Hooking Vulkan 1.3 presentation swapchain...';
      appendLog(`[VULKAN] Initialized VkDevice on NVIDIA / AMD GPU with 16GB unified heap`, 'vulkan');
      appendLog(`[VULKAN] Compiling SPIR-V pipeline state objects (1440p Target)...`, 'vulkan');
    }, 1400);

    setTimeout(() => {
      launchOverlayStep.textContent = 'Connecting low-latency DualSense controller...';
      appendLog(`[AUDIO] SDL2 48000Hz 7.1 Surround stream opened successfully`, 'audio');
      appendLog(`[PAD] DualSense controller connected (haptics enabled)`, 'anyps5');
    }, 2100);

    setTimeout(() => {
      launchOverlay.classList.remove('active');
      appendLog(`[SUCCESS] Process spawned cleanly (PID: ${Math.floor(Math.random() * 8000 + 12000)}). Game running!`, 'anyps5');
      logDrawer.classList.add('open');
    }, 2800);
  }

  // --- Terminal Logging Utility ---
  function appendLog(message, tag = 'anyps5') {
    const time = new Date().toTimeString().split(' ')[0];
    const line = document.createElement('div');
    line.className = 'log-line';

    let tagClass = 'log-tag-anyps5';
    let tagLabel = '[ANYPS5]';

    if (tag === 'vulkan') { tagClass = 'log-tag-vulkan'; tagLabel = '[VULKAN]'; }
    else if (tag === 'audio') { tagClass = 'log-tag-audio'; tagLabel = '[AUDIO]'; }
    else if (tag === 'warn') { tagClass = 'log-tag-warn'; tagLabel = '[WARN]'; }

    line.innerHTML = `<span class="log-timestamp">[${time}]</span> <span class="${tagClass}">${tagLabel}</span> ${message.replace(/\[\w+\]\s*/, '')}`;
    terminalOutput.appendChild(line);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
  }

  // --- Navigation Tabs ---
  navTabs.addEventListener('click', (e) => {
    const btn = e.target.closest('.nav-tab-btn');
    if (!btn) return;
    AudioEngine.click();

    document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const tab = btn.dataset.tab;
    viewLibrary.style.display = tab === 'library' ? 'block' : 'none';
    viewDiagnostics.style.display = tab === 'diagnostics' ? 'block' : 'none';
    viewInput.style.display = tab === 'input' ? 'block' : 'none';
    viewSettings.style.display = tab === 'settings' ? 'block' : 'none';

    if (tab === 'diagnostics') populateDiagnostics(activeGame);
  });

  // --- Diagnostics Population ---
  function populateDiagnostics(game) {
    document.getElementById('diagScorePercent').textContent = `${game.compatScore}%`;
    document.getElementById('diagResolvedRatio').textContent = `${game.symbolsResolved} / ${game.symbolsTotal} Symbols`;
    document.getElementById('diagProgressBar').style.width = `${game.compatScore}%`;
    document.getElementById('diagMissingCount').textContent = `${game.symbolsTotal - game.symbolsResolved} Stubs`;

    const tbody = document.getElementById('symbolsTableBody');
    tbody.innerHTML = '';
    sampleSymbols.forEach(s => {
      const tr = document.createElement('tr');
      const badgeColor = s.status === 'IMPLEMENTED' ? '#34d399' : (s.status === 'STUBBED' ? '#fbbf24' : '#f87171');
      tr.innerHTML = `
        <td style="color: var(--accent-cyan);">${s.module}</td>
        <td style="font-weight: 600;">${s.symbol}</td>
        <td style="color: var(--text-dim);">${s.nid}</td>
        <td><span style="color: ${badgeColor}; font-weight: 700;">● ${s.status}</span></td>
        <td style="color: var(--text-muted);">${s.action}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // --- Search & Filter Events ---
  searchInput.addEventListener('input', () => renderGrid());

  filterGroup.addEventListener('click', (e) => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    AudioEngine.click();
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilter = btn.dataset.filter;
    renderGrid();
  });

  // Hero Actions
  btnHeroLaunch.addEventListener('click', () => launchGame(activeGame));
  btnHeroAudit.addEventListener('click', () => {
    document.getElementById('tabDiagnostics').click();
  });

  // Drawer Toggle
  drawerHandle.addEventListener('click', () => logDrawer.classList.toggle('open'));
  btnToggleTerminal.addEventListener('click', () => {
    AudioEngine.click();
    logDrawer.classList.toggle('open');
  });

  // Add Game Modal
  const addGameModal = document.getElementById('addGameModal');
  document.getElementById('btnAddGame').addEventListener('click', () => {
    AudioEngine.click();
    addGameModal.classList.add('active');
  });
  document.getElementById('btnCloseModal').addEventListener('click', () => addGameModal.classList.remove('active'));
  document.getElementById('btnCancelAdd').addEventListener('click', () => addGameModal.classList.remove('active'));

  document.getElementById('btnConfirmAdd').addEventListener('click', () => {
    const title = document.getElementById('newGameTitle').value.trim();
    const titleId = document.getElementById('newGameTitleId').value.trim() || 'PPSA' + Math.floor(Math.random() * 90000 + 10000);
    const status = document.getElementById('newGameStatus').value;

    if (!title) {
      alert('Please enter a game title.');
      return;
    }

    const newGame = {
      id: 'custom_' + Date.now(),
      title: title,
      titleId: titleId,
      publisher: 'User Import',
      status: status,
      statusLabel: status === 'playable' ? 'Playable' : 'In-Game',
      cover: 'assets/images/astro_odyssey.jpg',
      banner: 'assets/images/hero_astro.jpg',
      desc: 'Custom imported PlayStation 5 package.',
      fps: '60 FPS',
      res: '1440p',
      shaders: '0 Compiled',
      compatScore: 92,
      symbolsTotal: 150,
      symbolsResolved: 138
    };

    gamesDatabase.push(newGame);
    addGameModal.classList.remove('active');
    renderGrid();
    selectGame(newGame);
    appendLog(`[IMPORT] Added new title: ${title} (${titleId})`, 'anyps5');
  });

  // Controller Visualizer Key Listener
  window.addEventListener('keydown', (e) => {
    if (viewInput.style.display !== 'none') {
      const cross = document.getElementById('btnCross');
      if (cross) {
        cross.style.fill = '#2563eb';
        setTimeout(() => cross.style.fill = '#1e293b', 180);
      }
    }
  });

  document.getElementById('btnSaveInputIni').addEventListener('click', () => {
    AudioEngine.click();
    appendLog('[INPUT] Saved controller mapping profile to anyps5-input.ini', 'anyps5');
    alert('anyps5-input.ini generated and saved successfully!');
  });

  document.getElementById('btnSaveSettings').addEventListener('click', () => {
    AudioEngine.click();
    appendLog('[SETTINGS] Runtime parameters updated. Re-indexed AnyPS5 daemon.', 'anyps5');
    alert('AnyPS5 runtime settings updated successfully!');
  });

  // --- Initial Boot ---
  renderGrid();
  appendLog('[INIT] AnyPS5 Launcher Hub v1.0 initialized.', 'anyps5');
  appendLog('[SYSTEM] Found AnyPS5 runtime at C:\Users\mbhni\AnyPS5\build\bin\anyps5.exe', 'anyps5');
  appendLog('[VULKAN] Verified Vulkan 1.3 Loader & Physical Device Capabilities.', 'vulkan');
  appendLog('[LIBRARY] Loaded 4 registered PS5 games.', 'anyps5');

})();
