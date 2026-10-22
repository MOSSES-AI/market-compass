/* Public official embeds + same-origin, hourly RSS snapshot. No bank credentials. */
(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  const categories = { ALL:'Semua', P:'P · Politik', E:'E · Ekonomi', S:'S · Sosial', T:'T · Teknologi', L:'L · Hukum', ENV:'E · Lingkungan', GEO:'Geopolitik' };
  const dateFmt = new Intl.DateTimeFormat('id-ID', {timeZone:'Asia/Jakarta',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
  const fmt = value => Number.isFinite(Date.parse(value)) ? dateFmt.format(new Date(value))+' WIB' : 'Belum tersedia';
  let snapshot = null, selected = 'ALL', hours = 72, busy = false, lastRead = null, loadFailed = false;

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function safeLink(value) {
    try { const url = new URL(value); return url.protocol === 'https:' && ['www.antaranews.com','antaranews.com'].includes(url.hostname) && !url.username && !url.password && !url.port ? url.href : null; } catch { return null; }
  }
  function newsItems() {
    const now = Date.now();
    return (Array.isArray(snapshot?.items) ? snapshot.items : []).filter(item => safeLink(item.url) && typeof item.title === 'string' && Number.isFinite(Date.parse(item.published_at)) && now-Date.parse(item.published_at) <= hours*3600000 && Date.parse(item.published_at) <= now+600000).sort((a,b)=>Date.parse(b.published_at)-Date.parse(a.published_at));
  }
  function outbound(title, url) {
    const a = el('a','',title); a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a;
  }
  function render() {
    const now = Date.now(), sources = Array.isArray(snapshot?.sources) ? snapshot.sources : [];
    const successes = sources.filter(s => s.status === 'ok' && now-Date.parse(s.last_success_at) < 3*3600000 && now-Date.parse(s.last_success_at) >= -600000);
    const stale = !snapshot || !Number.isFinite(Date.parse(snapshot.generated_at)) || now-Date.parse(snapshot.generated_at)>3*3600000 || successes.length !== sources.length || !sources.length;
    const oldRubrics = sources.filter(s=>!Number.isFinite(Date.parse(s.latest_published_at)) || now-Date.parse(s.latest_published_at)>72*3600000).length;
    const label = !snapshot ? 'Berita belum tersedia' : loadFailed ? 'Akses pembaruan gagal · menampilkan data terakhir' : stale ? `Perlu perhatian · ${successes.length}/${sources.length} sumber terpantau` : `${successes.length}/${sources.length} RSS berhasil diakses${oldRubrics ? ' · '+oldRubrics+' rubrik belum ada artikel dalam 72 jam' : ''}`;
    for (const node of document.querySelectorAll('[data-news-status]')) {node.textContent = label; node.classList.toggle('issue', stale || loadFailed);}
    for (const node of document.querySelectorAll('[data-news-checked]')) node.textContent = snapshot ? `Pemeriksaan server: ${fmt(snapshot.generated_at)} · halaman membaca: ${fmt(lastRead)}` : 'Memuat status pembaruan…';
    const statusBox = byId('feedStatuses'); statusBox.replaceChildren();
    for (const source of sources) {
      const recent = now-Date.parse(source.last_success_at) < 3*3600000;
      const oldArticle = !Number.isFinite(Date.parse(source.latest_published_at)) || now-Date.parse(source.latest_published_at)>72*3600000;
      const chip = el('span','source-chip'+(source.status !== 'ok' || !recent || oldArticle ? ' issue' : ''),`${source.label}: ${source.status === 'ok' && recent ? 'diakses' : 'gagal / data lama'} · artikel ${fmt(source.latest_published_at)}`);
      chip.title = `Terakhir berhasil mengambil RSS: ${fmt(source.last_success_at)}. Artikel terbaru: ${fmt(source.latest_published_at)}`;
      statusBox.append(chip);
    }
    const items = newsItems();
    byId('newsCount').textContent = `${items.length} judul dalam ${hours === 168 ? '7 hari' : hours+' jam'} · rubrik penerbit + tag kata pada judul`;
    const filtered = items.filter(item => selected === 'ALL' || item.categories?.includes(selected));
    const grid = byId('pestleNews'); grid.replaceChildren();
    for (const item of filtered.slice(0,36)) {
      const article = el('article','news-item'), heading = el('h3');
      heading.append(outbound(item.title, safeLink(item.url))); article.append(heading);
      const meta = el('div','news-meta');
      meta.append(el('span','','ANTARA'),el('time','',fmt(item.published_at)));
      if(item.feeds?.includes('terkini')) meta.append(el('span','news-category','tag kata judul'));
      for (const category of item.categories || []) if (categories[category]) meta.append(el('span','news-category',categories[category]));
      article.append(meta); grid.append(article);
    }
    if (!filtered.length) grid.append(el('p','news-empty',snapshot ? 'Tidak ada judul pada kategori dan rentang ini. Coba Semua atau 7 hari; status pengambilan sumber tetap ditampilkan.' : 'RSS belum berhasil dimuat. Buka sumber ANTARA atau coba muat ulang.'));
    const preview = byId('marketNewsPreview'); preview.replaceChildren();
    for (const item of items.filter(item=>item.categories?.includes('E') || item.categories?.includes('GEO')).slice(0,5)) {
      const a = outbound(item.title,safeLink(item.url)); a.append(el('small','',`ANTARA · ${fmt(item.published_at)}`)); preview.append(a);
    }
    if (!preview.children.length) preview.append(el('p','news-empty','Belum ada berita ekonomi/global dalam rentang terpilih.'));
  }
  async function refreshNews() {
    if (busy) return; busy = true;
    document.querySelectorAll('[data-refresh-news]').forEach(b=>b.disabled=true);
    try {
      const url = new URL('data/live.json', document.baseURI); url.searchParams.set('t',Date.now());
      const response = await fetch(url,{cache:'no-store',signal:AbortSignal.timeout(15000)});
      if (!response.ok) throw new Error('HTTP '+response.status);
      const next = await response.json();
      if (next.schema_version !== 1 || !Array.isArray(next.items) || !Array.isArray(next.sources)) throw new Error('Invalid news schema');
      snapshot = next; lastRead = new Date().toISOString(); loadFailed = false;
    } catch { loadFailed = true; }
    finally { busy = false; document.querySelectorAll('[data-refresh-news]').forEach(b=>b.disabled=false); render(); }
  }

  const common = {width:'100%',height:'100%',locale:'id',colorTheme:'light',isTransparent:false};
  const widgets = {
    ihsg: ['symbol-overview',{...common,symbols:[['IHSG','IDX:COMPOSITE|1D']],chartOnly:false,showVolume:true,hideDateRanges:false,dateRanges:['1m|1D','3m|1D','12m|1D'],dateFormat:'dd MMM yy',fontFamily:'Arial, sans-serif',scalePosition:'right',scaleMode:'Normal',chartType:'area'},'https://www.tradingview.com/symbols/IDX-COMPOSITE/','IHSG oleh TradingView'],
    gold: ['symbol-overview',{...common,symbols:[['Emas dunia · USD/oz','OANDA:XAUUSD|1D']],chartOnly:false,showVolume:false,hideDateRanges:false,dateRanges:['1d|1','1m|30','3m|60','12m|1D'],dateFormat:'dd MMM yy',fontFamily:'Arial, sans-serif',scalePosition:'right',scaleMode:'Normal',chartType:'area'},'https://www.tradingview.com/symbols/XAUUSD/','Emas dunia oleh TradingView'],
    watchlist:['market-quotes',{...common,showSymbolLogo:true,symbolsGroups:[{name:'Indeks · poin & saham · IDR',symbols:[{name:'IDX:COMPOSITE',displayName:'IHSG · poin'},{name:'IDX:BBCA',displayName:'BBCA'},{name:'IDX:BBRI',displayName:'BBRI'},{name:'IDX:BMRI',displayName:'BMRI'},{name:'IDX:ARTO',displayName:'ARTO'},{name:'IDX:HRTA',displayName:'HRTA · saham'},{name:'IDX:TLKM',displayName:'TLKM'}]}]},'https://www.tradingview.com/markets/stocks-indonesia/','Saham Indonesia oleh TradingView'],
    fx:['market-quotes',{...common,showSymbolLogo:true,symbolsGroups:[{name:'Indikasi pasar · per unit valas',symbols:[{name:'FX_IDC:USDIDR',displayName:'USD / IDR'},{name:'FX_IDC:SGDIDR',displayName:'SGD / IDR'},{name:'FX_IDC:CHFIDR',displayName:'CHF / IDR'},{name:'TVC:UKOIL',displayName:'Brent · USD/barel'}]}]},'https://www.tradingview.com/markets/currencies/','Pasar global oleh TradingView'],
    movers:['screener',{...common,market:'indonesia',defaultColumn:'overview',defaultScreen:'top_gainers',showToolbar:true},'https://www.tradingview.com/markets/stocks-indonesia/','Screener saham oleh TradingView']
  };
  function mountWidgets(force=false, only=null) {
    if (!byId('overview').classList.contains('active')) return;
    let requested = 0;
    for (const slot of document.querySelectorAll('[data-widget]')) {
      if (only && slot.dataset.widget !== only) continue;
      if (slot.dataset.mounted && !force) continue;
      const [name,config,url,credit] = widgets[slot.dataset.widget];
      slot.replaceChildren();
      const container = el('div','tradingview-widget-container'), inner = el('div','tradingview-widget-container__widget'), copyright = el('div','tradingview-widget-copyright');
      copyright.append(outbound(credit,url)); container.append(inner,copyright);
      const script = document.createElement('script'); script.async=true; script.src=`https://s3.tradingview.com/external-embedding/embed-widget-${name}.js`; script.textContent=JSON.stringify(config);
      script.onerror=()=>{inner.replaceChildren(el('p','news-empty','Feed tidak dapat dimuat. Gunakan tautan sumber di bawah; koneksi atau pemblokir konten dapat membatasi widget.'));};
      container.append(script); slot.append(container); slot.dataset.mounted='true';
      requested++;
    }
    if(requested) byId('widgetLoadedAt').textContent=`Permintaan feed: ${fmt(new Date().toISOString())}. Waktu ini bukan waktu kuotasi; lihat tanggal/sesi pada masing-masing feed.`;
  }
  function clock() {
    byId('liveClock').textContent = new Intl.DateTimeFormat('id-ID',{timeZone:'Asia/Jakarta',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date())+' WIB';
    byId('liveDay').textContent = new Intl.DateTimeFormat('id-ID',{timeZone:'Asia/Jakarta',weekday:'long',day:'numeric',month:'long',year:'numeric'}).format(new Date());
  }
  function init() {
    const filters = byId('pestleFilters');
    for (const [key,label] of Object.entries(categories)) {
      const button=el('button','news-filter'+(key==='ALL'?' active':''),label); button.type='button'; button.setAttribute('aria-pressed',String(key==='ALL'));
      button.addEventListener('click',()=>{selected=key;filters.querySelectorAll('button').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});render();}); filters.append(button);
    }
    byId('newsRange').addEventListener('change',event=>{hours=Number(event.target.value);render();});
    document.querySelectorAll('[data-refresh-news]').forEach(b=>b.addEventListener('click',refreshNews));
    byId('reloadMarket').addEventListener('click',()=>{mountWidgets(true);refreshNews();});
    document.querySelectorAll('[data-mover-screen]').forEach(button=>button.addEventListener('click',()=>{
      widgets.movers[1].defaultScreen=button.dataset.moverScreen;
      document.querySelectorAll('[data-mover-screen]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});
      mountWidgets(true,'movers');
    }));
    new MutationObserver(()=>mountWidgets()).observe(byId('overview'),{attributes:true,attributeFilter:['class']});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden) {clock();refreshNews();}});
    clock();mountWidgets();refreshNews();
    setInterval(clock,1000);setInterval(refreshNews,300000);setInterval(()=>{if(snapshot)render();},60000);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
})();
