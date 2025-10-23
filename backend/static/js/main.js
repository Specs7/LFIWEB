// Configuration de sécurité
// L'administration est maintenant gérée côté serveur (/admin/request).

// État de l'application
let articles = [
    {
        title: "L'Avenir en Commun pour Notre Ville",
        author: "Équipe de campagne LFI",
        date: "18 septembre 2025",
        image: "https://images.unsplash.com/photo-1577962917302-cd874c4e31d2?w=800&h=400&fit=crop",
        content: "Notre programme municipal s'inspire directement de l'Avenir en Commun. Nous proposons une transformation écologique et sociale de notre commune, avec la gratuité des transports, le développement des services publics et une démocratie participative renforcée."
    },
    {
        title: "Planification écologique municipale",
        author: "Commission Écologie LFI",
        date: "15 septembre 2025",
        image: "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800&h=400&fit=crop",
        content: "Face à l'urgence climatique, nous proposons un plan de transition écologique ambitieux : isolation thermique des bâtiments publics, développement des énergies renouvelables, protection de la biodiversité et agriculture urbaine."
    }
];

let mediaItems = [
    {
        title: "Marche pour le climat",
        description: "Mobilisation citoyenne LFI",
        image: "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=400&h=300&fit=crop"
    },
    {
        title: "Assemblée citoyenne",
        description: "Démocratie participative",
        image: "https://images.unsplash.com/photo-1511632765486-a01980e01a18?w=400&h=300&fit=crop"
    },
    {
        title: "L'Avenir en Commun",
        description: "Présentation du programme",
        image: "https://images.unsplash.com/photo-1582213782179-e0d53f98f2ca?w=400&h=300&fit=crop"
    }
];

let socialLinks = {
    facebook: "https://facebook.com/lafranceinsoumise",
    twitter: "https://twitter.com/lafranceinsoumise",
    instagram: "https://instagram.com/lafranceinsoumise",
    youtube: "https://youtube.com/lafranceinsoumise"
};

// Helpers: échappement et validation
function escapeHtml(str) {
    if (str === undefined || str === null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function isSafeUrl(url) {
    if (!url) return false;
    try {
        const u = new URL(url, location.href);
        return u.protocol === 'http:' || u.protocol === 'https:';
    } catch (e) {
        return false;
    }
}

function formatDate(date) {
    return new Date(date).toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Rendu sécurisé des articles et médias (évite innerHTML non échappé)
function renderArticles() {
    const container = document.getElementById('articles-container');
    container.innerHTML = '';
    // Public page: never show inline admin controls here. Full admin UI is
    // available only under /admin/manage which includes its own scripts.
    const isAdmin = false;
    articles.forEach(article => {
        const art = document.createElement('article');
        art.className = 'article';

        const h3 = document.createElement('h3');
        h3.textContent = article.title || '';

        const meta = document.createElement('div');
        meta.className = 'article-meta';
        meta.innerHTML = `<i class="fas fa-calendar"></i> ${escapeHtml(article.date)} | <i class="fas fa-user"></i> ${escapeHtml(article.author)}`;

        art.appendChild(h3);
        art.appendChild(meta);

        if (isSafeUrl(article.image)) {
            const img = document.createElement('img');
            img.src = article.image;
            img.alt = article.title ? article.title : 'Article image';
            art.appendChild(img);
        }

        const p = document.createElement('p');
        p.textContent = article.content || '';
        art.appendChild(p);
        // No inline admin controls on public pages.

        container.appendChild(art);
    });
}

function renderMedia() {
    const container = document.getElementById('media-container');
    container.innerHTML = '';
    mediaItems.forEach(item => {
        const div = document.createElement('div');
        div.className = 'media-item';

        if (isSafeUrl(item.image)) {
            const img = document.createElement('img');
            img.src = item.image;
            img.alt = item.title || 'Media image';
            div.appendChild(img);
        }

        const h4 = document.createElement('h4');
        h4.textContent = item.title || '';
        const p = document.createElement('p');
        p.textContent = item.description || '';

        div.appendChild(h4);
        div.appendChild(p);
        container.appendChild(div);
    });
}

function updateSocialLinks() {
    const socialElements = document.querySelectorAll('.social-links a');
    const links = [socialLinks.facebook, socialLinks.twitter, socialLinks.instagram, socialLinks.youtube];
    socialElements.forEach((element, index) => {
        const url = links[index];
        if (url && url !== '#' && isSafeUrl(url)) {
            element.href = url;
            element.target = '_blank';
            element.rel = 'noopener noreferrer';
        } else {
            element.removeAttribute('href');
        }
    });
}

// Gestionnaires d'événements : attachés après DOMContentLoaded pour sécurité
document.addEventListener('DOMContentLoaded', function() {
    // Admin functionality has been removed from client-side; use backend endpoints

    const articleForm = document.getElementById('articleForm');
    if (articleForm) {
        articleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            // Note: this client-side admin UI was removed; ensure backend access control
            const title = document.getElementById('articleTitle').value;
            const author = document.getElementById('articleAuthor').value;
            const image = document.getElementById('articleImage').value;
            const content = document.getElementById('articleContent').value;
            const newArticle = {
                title: escapeHtml(title),
                author: escapeHtml(author),
                date: formatDate(new Date()),
                image: isSafeUrl(image) ? image : '',
                content: content // content rendered as textContent later
            };
            articles.unshift(newArticle);
            renderArticles();
            this.reset();
            document.getElementById('articleAuthor').value = 'Équipe de campagne LFI';
            alert('Article publié avec succès !');
        });
    }

    const mediaFormEl = document.getElementById('mediaForm');
    if (mediaFormEl) {
        mediaFormEl.addEventListener('submit', function(e) {
            e.preventDefault();
            // Note: this client-side admin UI was removed; ensure backend access control
            const title = document.getElementById('mediaTitle').value;
            const description = document.getElementById('mediaDescription').value;
            const image = document.getElementById('mediaImage').value;
            const newMedia = {
                title: escapeHtml(title),
                description: escapeHtml(description),
                image: isSafeUrl(image) ? image : ''
            };
            mediaItems.push(newMedia);
            renderMedia();
            this.reset();
            alert('Image ajoutée à la galerie avec succès !');
        });
    }

    const socialFormEl = document.getElementById('socialForm');
    if (socialFormEl) {
        socialFormEl.addEventListener('submit', function(e) {
            e.preventDefault();
            // Note: this client-side admin UI was removed; ensure backend access control
            const fb = document.getElementById('facebookUrl').value;
            const tw = document.getElementById('twitterUrl').value;
            const ig = document.getElementById('instagramUrl').value;
            const yt = document.getElementById('youtubeUrl').value;
            if (isSafeUrl(fb)) socialLinks.facebook = fb;
            if (isSafeUrl(tw)) socialLinks.twitter = tw;
            if (isSafeUrl(ig)) socialLinks.instagram = ig;
            if (isSafeUrl(yt)) socialLinks.youtube = yt;
            updateSocialLinks();
            alert('Liens sociaux mis à jour avec succès !');
        });
    }

    // Smooth navigation
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // adminPanel removed

    // Session timeout removed (server-side authentication is used)

    // Animation on scroll
    function animateOnScroll() {
        const elements = document.querySelectorAll('.article, .media-item');
        elements.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;
            const elementVisible = 150;
            if (elementTop < window.innerHeight - elementVisible) {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }
        });
    }
    window.addEventListener('scroll', animateOnScroll);

    // Initialisation: try server-side articles, fallback to local articles
    fetch('/api/articles').then(r => {
        if (!r.ok) throw new Error('Network response not ok');
        return r.json();
    }).then(data => {
        if (data && Array.isArray(data.articles)) {
            articles = data.articles.map(a => ({
                id: a.id,
                title: a.title,
                author: a.author || 'Équipe de campagne LFI',
                date: a.created_at || '',
                image: a.image || '',
                content: a.content || ''
            }));
        }
        renderArticles();
    }).catch(err => {
        console.warn('Could not load articles from API, using local fallback:', err);
        renderArticles();
    }).finally(() => {
        renderMedia();
        updateSocialLinks();
        animateOnScroll();
    });
    // Admin UI is server-side. We still check /api/me to enable in-page admin
    // controls inside article render (the server-side admin page at /admin/manage
    // continues to handle full admin workflows). This fetch is kept minimal and
    // the code below only updates existing DOM controls if present.
    fetch('/api/me').then(r=>r.json()).then(data=>{
        if (data && data.user && data.user.role === 'admin') {
            // if the public page accidentally contains admin controls, make sure
            // we only touch them when present
            const panel = document.getElementById('admin-panel');
            if (panel) panel.style.display = 'block';
        }
    }).catch(()=>{});
    // Modal handlers for article edit
    // Edit modal handlers removed from public JS — admin editing belongs in
    // the /admin/manage template which includes the full admin scripts.
});
