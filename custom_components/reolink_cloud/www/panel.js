class ReolinkCloudPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._initialized) {
      this._initialized = true;
      this.render();
      this.loadVideos();
    }
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          padding: 16px;
          background: var(--primary-background-color);
          color: var(--primary-text-color);
          min-height: 100vh;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
        }
        h1 {
          margin: 0;
          font-size: 24px;
          font-weight: 500;
        }
        .date-nav {
          display: flex;
          gap: 8px;
          align-items: center;
        }
        .date-nav button {
          background: var(--primary-color);
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
        }
        .date-nav button:hover {
          opacity: 0.9;
        }
        .date-nav input {
          padding: 8px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
        }
        .video-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 16px;
        }
        .video-card {
          background: var(--card-background-color);
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .video-card img {
          width: 100%;
          height: 180px;
          object-fit: cover;
          cursor: pointer;
        }
        .video-card .info {
          padding: 12px;
        }
        .video-card .time {
          font-size: 14px;
          color: var(--secondary-text-color);
        }
        .video-card .actions {
          display: flex;
          gap: 8px;
          margin-top: 8px;
        }
        .video-card button {
          flex: 1;
          background: var(--primary-color);
          color: white;
          border: none;
          padding: 8px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
        }
        .video-modal {
          display: none;
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0,0,0,0.9);
          z-index: 1000;
          justify-content: center;
          align-items: center;
        }
        .video-modal.active {
          display: flex;
        }
        .video-modal video {
          max-width: 90%;
          max-height: 90%;
        }
        .video-modal .close {
          position: absolute;
          top: 20px;
          right: 20px;
          color: white;
          font-size: 32px;
          cursor: pointer;
        }
        .loading {
          text-align: center;
          padding: 40px;
          color: var(--secondary-text-color);
        }
        .empty {
          text-align: center;
          padding: 60px;
          color: var(--secondary-text-color);
        }
        .empty ha-icon {
          --mdc-icon-size: 64px;
          margin-bottom: 16px;
        }
        .refresh-btn {
          background: var(--primary-color);
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 4px;
          cursor: pointer;
        }
      </style>

      <div class="header">
        <h1>📹 Reolink Cloud Videos</h1>
        <div class="date-nav">
          <button id="prev-day">◀ Vorher</button>
          <input type="date" id="date-picker" />
          <button id="next-day">Nächster ▶</button>
          <button class="refresh-btn" id="refresh">🔄 Aktualisieren</button>
        </div>
      </div>

      <div id="content">
        <div class="loading">Lade Videos...</div>
      </div>

      <div class="video-modal" id="modal">
        <span class="close" id="close-modal">✕</span>
        <video id="video-player" controls></video>
      </div>
    `;

    // Set today's date
    const today = new Date().toISOString().split('T')[0];
    this.shadowRoot.getElementById('date-picker').value = today;
    this._currentDate = today;

    // Event listeners
    this.shadowRoot.getElementById('prev-day').addEventListener('click', () => this.changeDate(-1));
    this.shadowRoot.getElementById('next-day').addEventListener('click', () => this.changeDate(1));
    this.shadowRoot.getElementById('date-picker').addEventListener('change', (e) => {
      this._currentDate = e.target.value;
      this.loadVideos();
    });
    this.shadowRoot.getElementById('refresh').addEventListener('click', () => this.loadVideos());
    this.shadowRoot.getElementById('close-modal').addEventListener('click', () => this.closeModal());
    this.shadowRoot.getElementById('modal').addEventListener('click', (e) => {
      if (e.target.id === 'modal') this.closeModal();
    });
  }

  changeDate(delta) {
    const date = new Date(this._currentDate);
    date.setDate(date.getDate() + delta);
    this._currentDate = date.toISOString().split('T')[0];
    this.shadowRoot.getElementById('date-picker').value = this._currentDate;
    this.loadVideos();
  }

  async loadVideos() {
    const content = this.shadowRoot.getElementById('content');
    content.innerHTML = '<div class="loading">Lade Videos...</div>';

    try {
      const response = await fetch(`/api/reolink_cloud/videos/${this._currentDate}`);
      if (!response.ok) throw new Error('Failed to load videos');
      
      const data = await response.json();
      this.renderVideos(data.videos || []);
    } catch (error) {
      console.error('Error loading videos:', error);
      content.innerHTML = `
        <div class="empty">
          <div>📁</div>
          <p>Keine Videos für ${this._currentDate} gefunden</p>
          <p style="font-size: 12px;">Drücke "Download All Today" um Videos herunterzuladen</p>
        </div>
      `;
    }
  }

  renderVideos(videos) {
    const content = this.shadowRoot.getElementById('content');
    
    if (videos.length === 0) {
      content.innerHTML = `
        <div class="empty">
          <div>📁</div>
          <p>Keine Videos für ${this._currentDate} gefunden</p>
          <p style="font-size: 12px;">Drücke "Download All Today" um Videos herunterzuladen</p>
        </div>
      `;
      return;
    }

    content.innerHTML = `
      <div class="video-grid">
        ${videos.map(video => {
          const time = new Date(video.created * 1000).toLocaleTimeString('de-DE');
          const size = (video.size / 1024 / 1024).toFixed(1);
          const thumbUrl = video.has_thumbnail 
            ? video.thumbnail_url 
            : 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎬</text></svg>';
          return `
            <div class="video-card">
              <img src="${thumbUrl}" 
                   alt="${video.id}"
                   onclick="this.getRootNode().host.playVideo('${video.id}')"
                   onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎬</text></svg>'" />
              <div class="info">
                <div class="time">🕐 ${time} · ${size} MB</div>
                <div class="actions">
                  <button onclick="this.getRootNode().host.playVideo('${video.id}')">▶️ Abspielen</button>
                  <button onclick="this.getRootNode().host.downloadVideo('${video.id}')">⬇️ Download</button>
                </div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  playVideo(videoId) {
    const modal = this.shadowRoot.getElementById('modal');
    const player = this.shadowRoot.getElementById('video-player');
    player.src = `/media/reolink_cloud/${this._currentDate}/${videoId}.mp4`;
    modal.classList.add('active');
    player.play().catch(e => console.error('Play error:', e));
  }

  closeModal() {
    const modal = this.shadowRoot.getElementById('modal');
    const player = this.shadowRoot.getElementById('video-player');
    player.pause();
    player.src = '';
    modal.classList.remove('active');
  }

  downloadVideo(videoId) {
    const link = document.createElement('a');
    link.href = `/media/reolink_cloud/${this._currentDate}/${videoId}.mp4`;
    link.download = `reolink_${this._currentDate}_${videoId}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

customElements.define('reolink-cloud-panel', ReolinkCloudPanel);
