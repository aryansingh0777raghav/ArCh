/* ==========================================
   ArCh - AI Search Engine Frontend Controller
   Created by: Aryan Singh
   ========================================== */

const API_BASE = "http://127.0.0.1:8000";

// Application State
let currentHistoryId = null;
let activeView = "home";
let appSettings = {};
let activeSources = [];
let activeImages = [];
let triggeredByVoice = false;
let isDeepResearch = false;
let activeMode = "standard"; // "standard" or "storyboard"
let attachedDirectory = null;

// DOM Elements
const bodyEl = document.body;
const viewHome = document.getElementById("view-home");
const viewResults = document.getElementById("view-results");
const viewSettings = document.getElementById("view-settings");

const sidebarLogo = document.getElementById("sidebar-logo");
const btnNewSearch = document.getElementById("btn-new-search");
const btnSettings = document.getElementById("btn-settings");
const btnClearHistory = document.getElementById("btn-clear-history");
const historyList = document.getElementById("history-list");
const bookmarksList = document.getElementById("bookmarks-list");

const searchInput = document.getElementById("search-input");
const btnSubmitSearch = document.getElementById("btn-submit-search");
const btnVoice = document.getElementById("btn-voice");
const btnVoiceFollowup = document.getElementById("btn-voice-followup");
const btnSpeakAnswer = document.getElementById("btn-speak-answer");

const resultQueryTitle = document.getElementById("result-query-title");
const btnBookmarkThread = document.getElementById("btn-bookmark-thread");
const searchLoading = document.getElementById("search-loading");
const stepCrawl = document.getElementById("step-crawl");
const stepAi = document.getElementById("step-ai");
const resultsContainer = document.getElementById("results-container");

const chatThreadContainer = document.getElementById("chat-thread-container");
const aiAnswerBody = document.getElementById("ai-answer-body");
const btnCopyAnswer = document.getElementById("btn-copy-answer");
const keyFactsWrapper = document.getElementById("key-facts-wrapper");
const keyFactsList = document.getElementById("key-facts-list");
const followUpQuestions = document.getElementById("follow-up-questions");
const followUpInput = document.getElementById("follow-up-input");
const btnSubmitFollowUp = document.getElementById("btn-submit-follow-up");
const sourcesGrid = document.getElementById("sources-grid");

// Settings Elements
const settingGroqKey = document.getElementById("setting-groq-key");
const settingGroqModel = document.getElementById("setting-groq-model");
const settingTheme = document.getElementById("setting-theme");
const settingVoiceLang = document.getElementById("setting-voice-lang");
const btnSaveSettings = document.getElementById("btn-save-settings");
const settingsStatus = document.getElementById("settings-status");
const toast = document.getElementById("toast");

// Next-Gen UI Bindings
const tabModeStandard = document.getElementById("tab-mode-standard");
const tabModeStoryboard = document.getElementById("tab-mode-storyboard");
const toggleDeepResearch = document.getElementById("toggle-deep-research");
const btnAttachDir = document.getElementById("btn-attach-dir");
const btnAttachDirFollowup = document.getElementById("btn-attach-dir-followup");
const attachedDirBadge = document.getElementById("attached-dir-badge");
const attachedDirBadgeFollowup = document.getElementById("attached-dir-badge-followup");
const deepResearchBadgeFollowup = document.getElementById("deep-research-badge-followup");
const tabSources = document.getElementById("tab-sources");
const tabVisuals = document.getElementById("tab-visuals");
const sourcesTabContent = document.getElementById("sources-tab-content");
const visualsTabContent = document.getElementById("visuals-tab-content");
const visualsGrid = document.getElementById("visuals-grid");
const creatorSpotlightWrapper = document.getElementById("creator-spotlight-wrapper");
const btnCreatorHub = document.getElementById("btn-creator-hub");
const creatorHubModal = document.getElementById("creator-hub-modal");
const btnCloseCreatorHub = document.getElementById("btn-close-creator-hub");
const imageLightbox = document.getElementById("image-lightbox");
const lightboxImg = document.getElementById("lightbox-img");
const lightboxCaption = document.getElementById("lightbox-caption");
const closeLightbox = document.querySelector(".close-lightbox");

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
    setupWindowControls();
    loadSettings();
    loadHistory();
    loadBookmarks();
    setupEventListeners();
    setupAutoresizeTextarea();
});

// Title Bar Window Controls
function setupWindowControls() {
    document.getElementById("btn-minimize").addEventListener("click", () => {
        window.electronAPI.minimize();
    });
    document.getElementById("btn-maximize").addEventListener("click", () => {
        window.electronAPI.maximize();
    });
    document.getElementById("btn-close").addEventListener("click", () => {
        window.electronAPI.close();
    });
}

// Setup Event Listeners
function setupEventListeners() {
    // Logo Click triggers New Search
    sidebarLogo.addEventListener("click", startNewSearch);
    btnNewSearch.addEventListener("click", startNewSearch);
    
    // Switch to Settings
    btnSettings.addEventListener("click", () => {
        switchView("settings");
    });

    // Submit Search Home
    btnSubmitSearch.addEventListener("click", () => {
        triggeredByVoice = false;
        triggerHomeSearch();
    });
    searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            triggeredByVoice = false;
            triggerHomeSearch();
        }
    });

    // Voice search triggers
    btnVoice.addEventListener("click", toggleVoiceSearchHome);
    if (btnVoiceFollowup) {
        btnVoiceFollowup.addEventListener("click", toggleVoiceSearchFollowup);
    }

    // Speak AI summary answer trigger
    btnSpeakAnswer.addEventListener("click", toggleSpeakAnswer);

    // Suggestion Cards click
    document.querySelectorAll(".suggestion-card").forEach(card => {
        card.addEventListener("click", () => {
            const query = card.getAttribute("data-query");
            searchInput.value = query;
            triggeredByVoice = false;
            triggerHomeSearch();
        });
    });

    // Submit Follow Up
    btnSubmitFollowUp.addEventListener("click", () => {
        triggeredByVoice = false;
        triggerFollowUpSearch();
    });
    followUpInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            triggeredByVoice = false;
            triggerFollowUpSearch();
        }
    });

    // Copy AI Answer
    btnCopyAnswer.addEventListener("click", copyAnswerToClipboard);

    // Save/Bookmark Thread
    btnBookmarkThread.addEventListener("click", toggleBookmarkCurrentThread);

    // Save Settings
    btnSaveSettings.addEventListener("click", saveSettingsToServer);

    // Clear History
    btnClearHistory.addEventListener("click", clearAllHistory);

    // --- Next-Gen Event Listeners ---
    
    // Mode Switcher Tabs
    if (tabModeStandard && tabModeStoryboard) {
        tabModeStandard.addEventListener("click", () => {
            activeMode = "standard";
            tabModeStandard.classList.add("active");
            tabModeStoryboard.classList.remove("active");
            searchInput.placeholder = "Ask anything... (e.g. Who is Aryan Singh Filmmaker from Gorakhpur?)";
        });
        tabModeStoryboard.addEventListener("click", () => {
            activeMode = "storyboard";
            tabModeStoryboard.classList.add("active");
            tabModeStandard.classList.remove("active");
            searchInput.placeholder = "Storyboard mode active. Ask cinematic terms, script formatting, visual setups...";
        });
    }

    // Deep Research toggle
    if (toggleDeepResearch) {
        toggleDeepResearch.addEventListener("change", (e) => {
            isDeepResearch = e.target.checked;
            if (deepResearchBadgeFollowup) {
                if (isDeepResearch) {
                    deepResearchBadgeFollowup.className = "attached-dir-badge"; // Display active
                } else {
                    deepResearchBadgeFollowup.className = "badge-hidden";
                }
            }
        });
    }

    // Attach local folder buttons
    const handleAttachDir = async () => {
        try {
            if (window.electronAPI && window.electronAPI.selectDirectory) {
                const path = await window.electronAPI.selectDirectory();
                if (path) {
                    attachedDirectory = path;
                    showToast(`Attached local directory: ${path}`);
                    updateAttachedDirBadges();
                }
            } else {
                const path = prompt("Enter local folder path manually (e.g. C:\\Projects\\Screenplays):");
                if (path && path.trim()) {
                    attachedDirectory = path.trim();
                    showToast(`Attached local directory: ${attachedDirectory}`);
                    updateAttachedDirBadges();
                }
            }
        } catch (e) {
            console.error("Failed to select directory:", e);
        }
    };

    if (btnAttachDir) btnAttachDir.addEventListener("click", handleAttachDir);
    if (btnAttachDirFollowup) btnAttachDirFollowup.addEventListener("click", handleAttachDir);

    // Detach directories on badge click
    const handleDetachDir = () => {
        attachedDirectory = null;
        updateAttachedDirBadges();
        showToast("Local directory detached.");
    };
    if (attachedDirBadge) attachedDirBadge.addEventListener("click", handleDetachDir);
    if (attachedDirBadgeFollowup) attachedDirBadgeFollowup.addEventListener("click", handleDetachDir);

    // Sidebar Tab Switching
    if (tabSources && tabVisuals) {
        tabSources.addEventListener("click", () => {
            tabSources.classList.add("active");
            tabVisuals.classList.remove("active");
            sourcesTabContent.classList.add("active");
            visualsTabContent.classList.remove("active");
        });
        tabVisuals.addEventListener("click", () => {
            tabVisuals.classList.add("active");
            tabSources.classList.remove("active");
            visualsTabContent.classList.add("active");
            sourcesTabContent.classList.remove("active");
        });
    }

    // Creator Hub Modal
    if (btnCreatorHub) {
        btnCreatorHub.addEventListener("click", () => {
            creatorHubModal.classList.remove("hidden");
        });
    }
    if (btnCloseCreatorHub) {
        btnCloseCreatorHub.addEventListener("click", () => {
            creatorHubModal.classList.add("hidden");
        });
    }

    // Lightbox overlays click to close
    if (imageLightbox) {
        imageLightbox.addEventListener("click", () => {
            imageLightbox.classList.add("hidden");
        });
        closeLightbox.addEventListener("click", (e) => {
            e.stopPropagation();
            imageLightbox.classList.add("hidden");
        });
    }

    // Global ESC key listener to close modals
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            if (creatorHubModal) creatorHubModal.classList.add("hidden");
            if (imageLightbox) imageLightbox.classList.add("hidden");
        }
    });
}

// Textarea auto-resizing
function setupAutoresizeTextarea() {
    const textareas = [searchInput, followUpInput];
    textareas.forEach(textarea => {
        textarea.addEventListener("input", function() {
            this.style.height = "auto";
            this.style.height = (this.scrollHeight) + "px";
        });
    });
}

// Routing Management
function switchView(viewName) {
    activeView = viewName;
    
    viewHome.classList.remove("active");
    viewResults.classList.remove("active");
    viewSettings.classList.remove("active");
    
    btnSettings.classList.remove("active-btn");

    if (viewName === "home") {
        viewHome.classList.add("active");
        searchInput.value = "";
        searchInput.style.height = "auto";
        searchInput.focus();
    } else if (viewName === "results") {
        viewResults.classList.add("active");
    } else if (viewName === "settings") {
        viewSettings.classList.add("active");
        btnSettings.classList.add("active-btn");
    }
}

function startNewSearch() {
    currentHistoryId = null;
    btnBookmarkThread.classList.remove("bookmarked");
    btnBookmarkThread.querySelector("span").innerText = "Save Search";
    chatThreadContainer.innerHTML = "";
    stopSpeaking();
    switchView("home");
}

// Settings REST calls
async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE}/api/settings`);
        if (response.ok) {
            appSettings = await response.json();
            
            // Populate inputs
            settingGroqKey.value = appSettings.groq_api_key || "";
            settingGroqModel.value = appSettings.groq_model || "llama-3.3-70b-versatile";
            settingTheme.value = appSettings.theme || "dark";
            settingVoiceLang.value = appSettings.voice_lang || "en";
            
            applyTheme(appSettings.theme);
        }
    } catch (e) {
        console.error("Failed to load settings:", e);
    }
}

async function saveSettingsToServer() {
    const payload = {
        groq_api_key: settingGroqKey.value.trim(),
        groq_model: settingGroqModel.value,
        theme: settingTheme.value,
        voice_lang: settingVoiceLang.value
    };

    try {
        const response = await fetch(`${API_BASE}/api/settings`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            appSettings = await response.json();
            applyTheme(appSettings.theme);
            showToast("Configuration saved successfully!");
            loadHistory(); // Reload history in case provider changed display details
        } else {
            showToast("Failed to save configuration.", true);
        }
    } catch (e) {
        console.error(e);
        showToast("Error connecting to server.", true);
    }
}

function applyTheme(theme) {
    bodyEl.classList.remove("dark-theme", "light-theme");
    
    if (theme === "dark") {
        bodyEl.classList.add("dark-theme");
    } else if (theme === "light") {
        bodyEl.classList.add("light-theme");
    } else {
        // Auto: sync with system
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        bodyEl.classList.add(prefersDark ? "dark-theme" : "light-theme");
    }
}

// Toast Notification
function showToast(message, isError = false) {
    toast.innerText = message;
    toast.style.borderColor = isError ? "#ff4d4d" : "var(--border-color-active)";
    toast.classList.remove("toast-hidden");
    toast.classList.add("toast-visible");
    
    setTimeout(() => {
        toast.classList.remove("toast-visible");
        toast.classList.add("toast-hidden");
    }, 3000);
}

// History REST calls
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/api/history`);
        if (response.ok) {
            const history = await response.json();
            historyList.innerHTML = "";
            
            if (history.length === 0) {
                historyList.innerHTML = '<div class="list-empty">No searches yet</div>';
                return;
            }

            history.forEach(item => {
                const row = document.createElement("div");
                row.className = "history-item-row";
                row.setAttribute("data-id", item.id);
                
                row.innerHTML = `
                    <span class="item-title" title="${item.title}">${item.title}</span>
                    <button class="btn-delete-item" title="Delete Search">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                `;

                row.querySelector(".item-title").addEventListener("click", () => {
                    reopenSearch(item.id);
                });

                row.querySelector(".btn-delete-item").addEventListener("click", (e) => {
                    e.stopPropagation();
                    deleteHistoryItem(item.id);
                });

                historyList.appendChild(row);
            });
        }
    } catch (e) {
        console.error("Failed to load history:", e);
    }
}

async function deleteHistoryItem(id) {
    try {
        const response = await fetch(`${API_BASE}/api/history/delete`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id })
        });
        if (response.ok) {
            if (currentHistoryId === id) {
                startNewSearch();
            }
            loadHistory();
            loadBookmarks(); // Bookmarks are linked, reload both
        }
    } catch (e) {
        console.error(e);
    }
}

async function clearAllHistory() {
    if (!confirm("Are you sure you want to clear all search history?")) return;
    try {
        const response = await fetch(`${API_BASE}/api/history/clear`, {
            method: "POST"
        });
        if (response.ok) {
            startNewSearch();
            loadHistory();
            loadBookmarks();
        }
    } catch (e) {
        console.error(e);
    }
}

// Bookmarks (Saved Searches) REST calls
async function loadBookmarks() {
    try {
        const response = await fetch(`${API_BASE}/api/bookmarks`);
        if (response.ok) {
            const bookmarks = await response.json();
            bookmarksList.innerHTML = "";
            
            if (bookmarks.length === 0) {
                bookmarksList.innerHTML = '<div class="list-empty">No saved searches</div>';
                return;
            }

            bookmarks.forEach(item => {
                const row = document.createElement("div");
                row.className = "bookmark-item-row";
                row.setAttribute("data-id", item.history_id);
                
                row.innerHTML = `
                    <span class="item-title" title="${item.title}">${item.title}</span>
                    <button class="btn-delete-item" title="Remove Bookmark">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path></svg>
                    </button>
                `;

                row.querySelector(".item-title").addEventListener("click", () => {
                    reopenSearch(item.history_id);
                });

                row.querySelector(".btn-delete-item").addEventListener("click", (e) => {
                    e.stopPropagation();
                    removeBookmark(item.history_id);
                });

                bookmarksList.appendChild(row);
            });
        }
    } catch (e) {
        console.error("Failed to load bookmarks:", e);
    }
}

async function toggleBookmarkCurrentThread() {
    if (!currentHistoryId) return;
    
    const isBookmarked = btnBookmarkThread.classList.contains("bookmarked");
    if (isBookmarked) {
        await removeBookmark(currentHistoryId);
    } else {
        await addBookmark(currentHistoryId);
    }
}

async function addBookmark(historyId) {
    try {
        const response = await fetch(`${API_BASE}/api/bookmarks/add`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ history_id: historyId })
        });
        if (response.ok) {
            btnBookmarkThread.classList.add("bookmarked");
            btnBookmarkThread.querySelector("span").innerText = "Saved";
            showToast("Search saved to Bookmarks!");
            loadBookmarks();
        }
    } catch (e) {
        console.error(e);
    }
}

async function removeBookmark(historyId) {
    try {
        const response = await fetch(`${API_BASE}/api/bookmarks/remove`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ history_id: historyId })
        });
        if (response.ok) {
            if (currentHistoryId === historyId) {
                btnBookmarkThread.classList.remove("bookmarked");
                btnBookmarkThread.querySelector("span").innerText = "Save Search";
            }
            showToast("Removed from Saved Searches.");
            loadBookmarks();
        }
    } catch (e) {
        console.error(e);
    }
}

// Reopen search thread from history
async function reopenSearch(historyId) {
    try {
        const response = await fetch(`${API_BASE}/api/history`);
        if (response.ok) {
            const history = await response.json();
            const thread = history.find(item => item.id === historyId);
            
            if (thread && thread.messages.length > 0) {
                currentHistoryId = historyId;
                switchView("results");
                
                resultQueryTitle.innerText = thread.title;
                
                // Set bookmarked visual state
                checkBookmarkState(historyId);
                
                // Render previous turns and latest turn
                renderCompleteThread(thread.messages);
                
                // Scroll to top
                viewResults.scrollTop = 0;
            }
        }
    } catch (e) {
        console.error(e);
        showToast("Error loading saved thread", true);
    }
}

async function checkBookmarkState(historyId) {
    try {
        const response = await fetch(`${API_BASE}/api/bookmarks`);
        if (response.ok) {
            const bookmarks = await response.json();
            const exists = bookmarks.some(b => b.history_id === historyId);
            if (exists) {
                btnBookmarkThread.classList.add("bookmarked");
                btnBookmarkThread.querySelector("span").innerText = "Saved";
            } else {
                btnBookmarkThread.classList.remove("bookmarked");
                btnBookmarkThread.querySelector("span").innerText = "Save Search";
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// Search Processing
function triggerHomeSearch() {
    const query = searchInput.value.trim();
    if (!query) return;
    executeSearch(query);
}

function triggerFollowUpSearch() {
    const query = followUpInput.value.trim();
    if (!query) return;
    followUpInput.value = "";
    followUpInput.style.height = "auto";
    executeSearch(query);
}

async function executeSearch(query) {
    stopSpeaking();
    switchView("results");
    
    // Configure Loading state
    resultsContainer.style.display = "none";
    searchLoading.style.display = "flex";
    
    stepCrawl.className = "step-item active";
    stepAi.className = "step-item";
    
    resultQueryTitle.innerText = query;
    
    // Trigger Instant voice easter egg replies if query matches creator questions
    const lowerQ = query.toLowerCase();
    if (lowerQ.includes("who created you") || lowerQ.includes("arch ko kisne banaya") || lowerQ.includes("who made you") || lowerQ.includes("who is your creator") || lowerQ.includes("tumhe kisne banaya")) {
        const isHindi = lowerQ.includes("kisne") || lowerQ.includes("banaya") || (appSettings && appSettings.voice_lang === "hi");
        const voiceText = isHindi 
            ? "Mujhe Aryan Singh ne banaya hai, jo ek developer aur filmmaker hain."
            : "I was created by Aryan Singh, a developer and filmmaker.";
        speakInstantEasterEgg(voiceText);
    }
    
    // Display or hide creator spotlight card
    if (lowerQ.includes("aryan singh") || lowerQ.includes("creator") || lowerQ.includes("developer") || lowerQ.includes("filmmaker")) {
        if (creatorSpotlightWrapper) {
            creatorSpotlightWrapper.className = "creator-spotlight-visible";
        }
    } else {
        if (creatorSpotlightWrapper) {
            creatorSpotlightWrapper.className = "creator-spotlight-hidden";
        }
    }
    
    const payload = {
        query: query,
        history_id: currentHistoryId,
        deep_research: isDeepResearch,
        local_dir: attachedDirectory,
        storyboard_mode: (activeMode === "storyboard")
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error(`Server returned error status: ${response.status}`);
        }
        
        stepCrawl.className = "step-item";
        stepAi.className = "step-item active";
        
        const data = await response.json();
        
        currentHistoryId = data.history_id;
        activeSources = data.sources;
        activeImages = data.images || [];
        
        // Hide loading, show results
        searchLoading.style.display = "none";
        resultsContainer.style.display = "grid";
        
        // Render sources
        renderSources(data.sources);
        
        // Render visuals grid
        renderVisuals(activeImages);
        
        // Render answer
        aiAnswerBody.innerHTML = renderMarkdown(data.ai_answer);
        setupCitationPillListeners();
        
        // Render facts
        renderKeyFacts(data.key_facts);
        
        // Render follow-ups
        renderFollowUps(data.follow_ups);
        
        // Render chat log if multi-turn
        await reloadChatThreadHistory();
        
        // Sync history list
        loadHistory();
        checkBookmarkState(currentHistoryId);
        
        // Scroll results view to top
        viewResults.scrollTop = 0;

        // Auto-play TTS if triggered by voice
        if (triggeredByVoice) {
            triggeredByVoice = false;
            setTimeout(() => {
                toggleSpeakAnswer();
            }, 600);
        }
        
    } catch (e) {
        console.error("Search failed:", e);
        searchLoading.style.display = "none";
        resultsContainer.style.display = "grid";
        aiAnswerBody.innerHTML = `
            <h3>⚠️ Connection Error</h3>
            <p>Could not connect to the ArCh FastAPI backend server. Details: ${e.message}</p>
            <p>Please make sure the backend Python server is running and check your network connection.</p>
        `;
        sourcesGrid.innerHTML = '<div class="list-empty">No sources found</div>';
        if (visualsGrid) {
            visualsGrid.innerHTML = '<div class="list-empty">No images found</div>';
        }
        keyFactsWrapper.style.display = "none";
        followUpQuestions.innerHTML = "";
    }
}

// Dynamic UI Renderers

function renderSources(sources) {
    sourcesGrid.innerHTML = "";
    if (!sources || sources.length === 0) {
        sourcesGrid.innerHTML = '<div class="list-empty">No web sources found</div>';
        return;
    }
    
    sources.forEach((source, index) => {
        const domain = getDomainName(source.url);
        const card = document.createElement("div");
        card.className = "source-card";
        card.setAttribute("id", `source-${index + 1}`);
        
        card.innerHTML = `
            <div class="source-card-header">
                <span class="source-index">${index + 1}</span>
                <span class="source-title">${source.title}</span>
            </div>
            <div class="source-snippet">${source.snippet}</div>
            <div class="source-domain">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
                <span>${domain}</span>
            </div>
        `;
        
        card.addEventListener("click", () => {
            window.electronAPI.openExternal(source.url);
        });
        
        sourcesGrid.appendChild(card);
    });
}

function renderKeyFacts(facts) {
    keyFactsList.innerHTML = "";
    if (!facts || facts.length === 0) {
        keyFactsWrapper.style.display = "none";
        return;
    }
    
    keyFactsWrapper.style.display = "flex";
    facts.forEach(fact => {
        const li = document.createElement("li");
        li.innerText = fact;
        keyFactsList.appendChild(li);
    });
}

function renderFollowUps(questions) {
    followUpQuestions.innerHTML = "";
    if (!questions || questions.length === 0) return;
    
    questions.forEach(q => {
        const btn = document.createElement("button");
        btn.className = "btn-follow-up-pill";
        btn.innerText = q;
        
        btn.addEventListener("click", () => {
            executeSearch(q);
        });
        
        followUpQuestions.appendChild(btn);
    });
}

// Render complete conversational thread for reopened history
function renderCompleteThread(messages) {
    chatThreadContainer.innerHTML = "";
    
    // The history contains alternate turns: User, Assistant, User, Assistant
    // The final turn is rendered in the main card (AI Summary + key facts + sources)
    // All previous turns are rendered sequentially in the chatThreadContainer
    
    if (messages.length <= 2) {
        // Only 1 turn, nothing to show in previous logs
        renderLatestTurnOnly(messages[0], messages[1]);
        return;
    }
    
    // Extract turns
    for (let i = 0; i < messages.length - 2; i += 2) {
        const userMsg = messages[i];
        const assistantMsg = messages[i + 1];
        let assistantData = {};
        
        try {
            assistantData = JSON.parse(assistantMsg.content);
        } catch (e) {
            assistantData = { answer: assistantMsg.content, key_facts: [], follow_ups: [] };
        }
        
        // Create turn wrapper
        const turnDiv = document.createElement("div");
        turnDiv.className = "chat-turn-block";
        
        // Add User query title
        const userTitle = document.createElement("div");
        userTitle.className = "chat-turn-user";
        userTitle.innerText = userMsg.content;
        turnDiv.appendChild(userTitle);
        
        // Add AI summary card
        const aiCard = document.createElement("div");
        aiCard.className = "result-card";
        aiCard.style.marginTop = "12px";
        
        aiCard.innerHTML = `
            <div class="card-header">
                <div class="header-title">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                    <span>AI summary</span>
                </div>
            </div>
            <div class="card-content answer-markdown">
                ${renderMarkdown(assistantData.answer)}
            </div>
        `;
        
        turnDiv.appendChild(aiCard);
        chatThreadContainer.appendChild(turnDiv);
    }
    
    // Render the latest turn in the main results container
    const lastUser = messages[messages.length - 2];
    const lastAssistant = messages[messages.length - 1];
    renderLatestTurnOnly(lastUser, lastAssistant);
}

function renderLatestTurnOnly(userMsg, assistantMsg) {
    let assistantData = {};
    try {
        assistantData = JSON.parse(assistantMsg.content);
    } catch (e) {
        assistantData = { answer: assistantMsg.content, key_facts: [], follow_ups: [] };
    }
    
    activeSources = assistantMsg.sources || [];
    activeImages = assistantMsg.images || [];
    
    // Render latest query
    resultQueryTitle.innerText = userMsg.content;
    
    // Render main card content
    aiAnswerBody.innerHTML = renderMarkdown(assistantData.answer);
    setupCitationPillListeners();
    
    // Render key facts
    renderKeyFacts(assistantData.key_facts);
    
    // Render follow ups
    renderFollowUps(assistantData.follow_ups);
    
    // Render sources
    renderSources(activeSources);

    // Render visuals grid
    renderVisuals(activeImages);

    // Display/hide Creator Spotlight
    const lowerQ = userMsg.content.toLowerCase();
    if (lowerQ.includes("aryan singh") || lowerQ.includes("creator") || lowerQ.includes("developer") || lowerQ.includes("filmmaker")) {
        if (creatorSpotlightWrapper) {
            creatorSpotlightWrapper.className = "creator-spotlight-visible";
        }
    } else {
        if (creatorSpotlightWrapper) {
            creatorSpotlightWrapper.className = "creator-spotlight-hidden";
        }
    }
}

async function reloadChatThreadHistory() {
    if (!currentHistoryId) return;
    try {
        const response = await fetch(`${API_BASE}/api/history`);
        if (response.ok) {
            const history = await response.json();
            const thread = history.find(item => item.id === currentHistoryId);
            if (thread && thread.messages.length > 2) {
                renderCompleteThread(thread.messages);
            } else {
                chatThreadContainer.innerHTML = "";
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// Copy Answer to clipboard helper
function copyAnswerToClipboard() {
    // Get text content of AI Answer
    const text = aiAnswerBody.innerText;
    navigator.clipboard.writeText(text).then(() => {
        showToast("Answer copied to clipboard!");
    }).catch(err => {
        console.error("Failed to copy:", err);
    });
}

// URL/Domain Helper
function getDomainName(urlStr) {
    try {
        const url = new URL(urlStr);
        return url.hostname.replace("www.", "");
    } catch (e) {
        return urlStr;
    }
}

// Click listener for Citations linking
function setupCitationPillListeners() {
    document.querySelectorAll(".citation-pill").forEach(pill => {
        pill.addEventListener("click", (e) => {
            e.stopPropagation();
            const index = pill.getAttribute("data-index");
            const targetCard = document.getElementById(`source-${index}`);
            if (targetCard) {
                // Scroll source card into view smoothly
                targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
                
                // Add highlight animation glow
                targetCard.style.boxShadow = "0 0 15px rgba(0, 242, 254, 0.4)";
                targetCard.style.borderColor = "var(--accent-blue)";
                
                setTimeout(() => {
                    targetCard.style.boxShadow = "none";
                    targetCard.style.borderColor = "var(--border-color)";
                }, 1800);
            }
        });
    });
}

// Markdown-to-HTML parser (Offline-ready, parses markdown and citations)
function renderMarkdown(md) {
    if (!md) return "";
    let html = md;

    // Escaping html characters to prevent script injections
    html = html
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Code blocks: ```javascript ... ```
    html = html.replace(/```(\w*)\n([\s\S]*?)\n```/g, (match, lang, code) => {
        if (lang === "screenplay") {
            const screenplayLines = code.split("\n");
            let formattedScreenplay = "";
            let lastWasCharacter = false;
            let lastWasParenthetical = false;
            
            screenplayLines.forEach(line => {
                const trimmed = line.trim();
                if (!trimmed) {
                    formattedScreenplay += "<span style='display:block; height:12px;'></span>";
                    return;
                }
                
                if (/^(INT\.|EXT\.|INT\/EXT\.|EST\.|MONTAGE|SCENE)/i.test(trimmed)) {
                    formattedScreenplay += `<span class="screenplay-scene-heading">${trimmed}</span>`;
                    lastWasCharacter = false;
                    lastWasParenthetical = false;
                }
                else if (trimmed.startsWith("(") && trimmed.endsWith(")")) {
                    formattedScreenplay += `<span class="screenplay-parenthetical">${trimmed}</span>`;
                    lastWasCharacter = false;
                    lastWasParenthetical = true;
                }
                else if (trimmed === trimmed.toUpperCase() && trimmed.length < 30 && !trimmed.endsWith(":") && !trimmed.endsWith(".")) {
                    formattedScreenplay += `<span class="screenplay-character">${trimmed}</span>`;
                    lastWasCharacter = true;
                    lastWasParenthetical = false;
                }
                else {
                    if (lastWasCharacter || lastWasParenthetical) {
                        formattedScreenplay += `<span class="screenplay-dialogue">${trimmed}</span>`;
                    } else {
                        formattedScreenplay += `<span class="screenplay-action">${trimmed}</span>`;
                        lastWasCharacter = false;
                        lastWasParenthetical = false;
                    }
                }
            });
            return `<pre class="code-block language-screenplay">${formattedScreenplay}</pre>`;
        }
        return `<pre class="code-block"><code class="language-${lang}">${code}</code></pre>`;
    });

    // Inline code: `code`
    html = html.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>');

    // Tables:
    const lines = html.split('\n');
    let inTable = false;
    let tableHtml = "";
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.startsWith('|') && line.endsWith('|')) {
            if (!inTable) {
                inTable = true;
                tableHtml = '<table class="markdown-table"><thead>';
                const cols = line.split('|').map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
                tableHtml += '<tr>' + cols.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>';
                // Skip next line if it is separator | --- |
                if (i + 1 < lines.length && lines[i+1].includes('---')) {
                    i++;
                }
            } else {
                const cols = line.split('|').map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
                tableHtml += '<tr>' + cols.map(c => `<td>${c}</td>`).join('') + '</tr>';
            }
            lines[i] = ""; // Clear line
        } else {
            if (inTable) {
                inTable = false;
                tableHtml += '</tbody></table>';
                lines[i] = tableHtml + '\n' + lines[i];
            }
        }
    }
    html = lines.join('\n');

    // Headings
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Strong / Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Emphasis / Italic
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Unordered Lists: - item or * item
    html = html.replace(/^\s*[-*]\s+(.*$)/gim, '<ul><li>$1</li></ul>');
    // Clean up adjacent ul tags
    html = html.replace(/<\/ul>\s*<ul>/g, '');

    // Ordered Lists: 1. item
    html = html.replace(/^\s*\d+\.\s+(.*$)/gim, '<ol><li>$1</li></ol>');
    // Clean up adjacent ol tags
    html = html.replace(/<\/ol>\s*<ol>/g, '');

    // Links: [text](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
        // Protect single citation pills wrapped in brackets inside markdown links
        if (/^\d+$/.test(text)) {
             return `<span class="citation-pill" data-index="${text}">[${text}]</span>`;
        }
        return `<a href="#" onclick="window.electronAPI.openExternal('${url}'); return false;">${text}</a>`;
    });

    // Citations System: e.g. [1] or [2]
    // Turn citations into clean pill buttons that map to the source items
    html = html.replace(/\[(\d+)\]/g, '<span class="citation-pill" data-index="$1">[$1]</span>');

    // Line breaks
    html = html.replace(/\n\n/g, '<br><br>');
    
    return html;
}

// ==========================================
// Speech-to-Text & Text-to-Speech Integration
// ==========================================

let isListening = false;
let sttController = null;
let activeMicButton = null;

function toggleVoiceSearchHome() {
    if (isListening) {
        stopListening();
    } else {
        startListening(searchInput, btnVoice);
    }
}

function toggleVoiceSearchFollowup() {
    if (isListening) {
        stopListening();
    } else {
        startListening(followUpInput, btnVoiceFollowup);
    }
}

function startListening(inputElement, buttonElement) {
    stopSpeaking();
    isListening = true;
    triggeredByVoice = true;
    activeMicButton = buttonElement;
    
    // Visual indicator: pulse microphone button
    if (activeMicButton) {
        activeMicButton.style.color = "#ff4d4d";
        activeMicButton.style.filter = "drop-shadow(0 0 8px rgba(255, 77, 77, 0.6))";
    }
    showToast("Listening... Speak now.");
    
    // Set up AbortController to support stopping the microphone early
    sttController = new AbortController();
    const signal = sttController.signal;
    
    // Fetch Vosk transcription from local server
    const lang = appSettings.voice_lang || "en";
    fetch(`${API_BASE}/api/stt?lang=${lang}`, { signal })
        .then(res => res.json())
        .then(data => {
            if (isListening) {
                const transcript = data.text ? data.text.trim() : "";
                if (transcript) {
                    inputElement.value = transcript;
                    // Trigger textarea auto-resize
                    inputElement.style.height = "auto";
                    inputElement.style.height = (inputElement.scrollHeight) + "px";
                    showToast(`Recognized: "${transcript}"`);
                    
                    // Auto-execute search
                    setTimeout(() => {
                        executeSearch(transcript);
                    }, 800);
                } else {
                    showToast("No speech detected.", true);
                }
            }
            stopListening();
        })
        .catch(err => {
            if (err.name === 'AbortError') {
                console.log("Speech recognition aborted by user.");
            } else {
                console.error("STT Error:", err);
                showToast("Speech recognition failed.", true);
            }
            stopListening();
        });
}

function stopListening() {
    isListening = false;
    if (activeMicButton) {
        activeMicButton.style.color = "var(--text-muted)";
        activeMicButton.style.filter = "none";
        activeMicButton = null;
    }
    if (sttController) {
        sttController.abort();
        sttController = null;
    }
}

// Text-to-Speech Playback (Piper / SAPI)
let currentAudio = null;
let isSpeaking = false;

function toggleSpeakAnswer() {
    if (isSpeaking) {
        stopSpeaking();
        return;
    }
    
    const answerText = aiAnswerBody.innerText;
    if (!answerText || answerText.trim().length === 0) {
        showToast("No text content to read.", true);
        return;
    }
    
    isSpeaking = true;
    btnSpeakAnswer.style.color = "var(--accent-blue)";
    btnSpeakAnswer.style.filter = "drop-shadow(0 0 4px rgba(0, 242, 254, 0.5))";
    // Pause SVG icon
    btnSpeakAnswer.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>`;
    
    showToast("Generating voice narration...");
    
    fetch(`${API_BASE}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: answerText })
    })
    .then(res => {
        if (!res.ok) throw new Error("TTS generation failed");
        return res.blob();
    })
    .then(blob => {
        if (!isSpeaking) return; // User stopped it during generation
        const audioUrl = URL.createObjectURL(blob);
        currentAudio = new Audio(audioUrl);
        currentAudio.play().then(() => {
            currentAudio.onended = () => {
                stopSpeaking();
                URL.revokeObjectURL(audioUrl);
            };
        }).catch(err => {
            console.error("Audio playback error:", err);
            showToast("Audio playback failed.", true);
            stopSpeaking();
            URL.revokeObjectURL(audioUrl);
        });
    })
    .catch(err => {
        console.error("Audio generation error:", err);
        showToast("Audio generation failed.", true);
        stopSpeaking();
    });
}

function stopSpeaking() {
    isSpeaking = false;
    if (btnSpeakAnswer) {
        btnSpeakAnswer.style.color = "var(--text-secondary)";
        btnSpeakAnswer.style.filter = "none";
        // Speaker SVG icon
        btnSpeakAnswer.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>`;
    }
    if (currentAudio) {
        currentAudio.pause();
        if (currentAudio.src && currentAudio.src.startsWith("blob:")) {
            URL.revokeObjectURL(currentAudio.src);
        }
        currentAudio = null;
    }
}

// --- Next-Gen Helper Functions ---

function updateAttachedDirBadges() {
    if (attachedDirectory) {
        const basename = getFolderBasename(attachedDirectory);
        if (attachedDirBadge) {
            attachedDirBadge.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:2px;"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>${basename}`;
            attachedDirBadge.className = "attached-dir-badge";
        }
        if (attachedDirBadgeFollowup) {
            attachedDirBadgeFollowup.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:2px;"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>${basename}`;
            attachedDirBadgeFollowup.className = "attached-dir-badge";
        }
    } else {
        if (attachedDirBadge) attachedDirBadge.className = "badge-hidden";
        if (attachedDirBadgeFollowup) attachedDirBadgeFollowup.className = "badge-hidden";
    }
}

function getFolderBasename(pathStr) {
    if (!pathStr) return "";
    const parts = pathStr.split(/[/\\]/);
    return parts[parts.length - 1] || pathStr;
}

function renderVisuals(images) {
    if (!visualsGrid) return;
    visualsGrid.innerHTML = "";
    
    if (!images || images.length === 0) {
        visualsGrid.innerHTML = '<div class="list-empty">No visual references found</div>';
        return;
    }
    
    images.forEach((imgUrl, index) => {
        const card = document.createElement("div");
        card.className = "visual-card";
        
        card.innerHTML = `
            <img src="${imgUrl}" class="visual-image" loading="lazy" alt="Reference Frame ${index + 1}">
            <div class="visual-card-overlay">
                <div class="visual-card-title">Frame #${index + 1}</div>
            </div>
        `;
        
        card.addEventListener("click", () => {
            if (imageLightbox && lightboxImg && lightboxCaption) {
                lightboxImg.src = imgUrl;
                lightboxCaption.innerText = `Reference Frame #${index + 1} (${imgUrl})`;
                imageLightbox.classList.remove("hidden");
            }
        });
        
        visualsGrid.appendChild(card);
    });
}

function speakInstantEasterEgg(text) {
    fetch(`${API_BASE}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
    })
    .then(res => {
        if (!res.ok) throw new Error("TTS synthesis failed");
        return res.blob();
    })
    .then(blob => {
        const audioUrl = URL.createObjectURL(blob);
        const easterEggAudio = new Audio(audioUrl);
        easterEggAudio.play().then(() => {
            easterEggAudio.onended = () => {
                URL.revokeObjectURL(audioUrl);
            };
        }).catch(err => {
            console.error("Instant voice synthesis playback failed:", err);
            URL.revokeObjectURL(audioUrl);
        });
    })
    .catch(e => console.error("Easter egg voice synthesis endpoint error:", e));
}
