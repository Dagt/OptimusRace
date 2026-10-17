(() => {
  const viewer = document.querySelector('[data-gallery-viewer]');
  const links = [...document.querySelectorAll('[data-gallery-photo]')];
  if (viewer && typeof viewer.showModal === 'function') {
    const full = viewer.querySelector('[data-gallery-full]');
    const previous = viewer.querySelector('[data-gallery-prev]');
    const next = viewer.querySelector('[data-gallery-next]');
    let current = 0;
    let trigger;
    const show = index => {
      current = index;
      const link = links[index];
      full.alt = link.querySelector('img').alt;
      full.src = link.dataset.preview;
      viewer.querySelector('[data-gallery-caption]').textContent = link.dataset.caption;
      viewer.querySelector('[data-gallery-counter]').textContent = `Foto ${index + 1} de ${links.length} en esta página`;
      previous.disabled = index === 0;
      next.disabled = index === links.length - 1;
    };
    links.forEach((link, index) => link.addEventListener('click', event => {
      event.preventDefault();
      trigger = link;
      show(index);
      viewer.showModal();
    }));
    previous.addEventListener('click', () => { if (current > 0) show(current - 1); });
    next.addEventListener('click', () => { if (current < links.length - 1) show(current + 1); });
    viewer.querySelector('[data-gallery-close]').addEventListener('click', () => viewer.close());
    viewer.addEventListener('keydown', event => {
      if (event.key === 'ArrowLeft' && current > 0) { event.preventDefault(); show(current - 1); }
      if (event.key === 'ArrowRight' && current < links.length - 1) { event.preventDefault(); show(current + 1); }
    });
    viewer.addEventListener('close', () => { full.removeAttribute('src'); trigger?.focus(); });
  }
  // Discourage the browser's ordinary save/drag actions; the embedded watermark
  // protects the viewing copy even when browser tools or screenshots are used.
  document.querySelectorAll('.gallery-photo img, [data-gallery-full], .gallery-cover img').forEach(image => {
    image.addEventListener('contextmenu', event => event.preventDefault());
    image.addEventListener('dragstart', event => event.preventDefault());
  });
  const upload = document.querySelector('[data-gallery-upload]');
  if (upload) {
    const input = upload.querySelector('input[type=file]');
    const status = upload.querySelector('[data-gallery-upload-status]');
    input.addEventListener('change', () => {
      const files = [...input.files];
      const size = files.reduce((sum, file) => sum + file.size, 0);
      const error = files.length > 20 ? 'Selecciona hasta 20 fotos.' :
        size > 100 * 1024 * 1024 ? 'El envío supera los 100 MB.' :
        files.some(file => file.size > 15 * 1024 * 1024) ? 'Cada foto debe pesar menos de 15 MB.' : '';
      input.setCustomValidity(error);
      status.textContent = error || (files.length ? `${files.length} fotos seleccionadas · ${(size / (1024 * 1024)).toFixed(1)} MB` : '');
    });
    upload.addEventListener('submit', () => {
      if (!upload.checkValidity()) return;
      status.textContent = 'Subiendo fotos y aplicando la marca de agua. Espera a que termine…';
      upload.querySelector('button[type=submit]').disabled = true;
    });
  }
})();
