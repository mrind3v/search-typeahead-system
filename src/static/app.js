// Frontend typeahead UI (Phase 4).

const DEBOUNCE_MS = 300;
const MIN_PREFIX_LENGTH = 3;

const searchInput = document.getElementById("search-input");
const suggestionsList = document.getElementById("suggestions");

let debounceTimer = null;

function clearSuggestions() {
  suggestionsList.replaceChildren();
}

function renderSuggestions(items) {
  clearSuggestions();
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = `${item.query} (${item.count})`;
    suggestionsList.appendChild(li);
  }
}

async function fetchSuggestions(prefix) {
  const response = await fetch(`/suggest?q=${encodeURIComponent(prefix)}`);
  if (!response.ok) {
    clearSuggestions();
    return;
  }
  const data = await response.json();
  renderSuggestions(data);
}

searchInput.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  const value = searchInput.value.trim();

  if (value.length < MIN_PREFIX_LENGTH) {
    clearSuggestions();
    return;
  }

  debounceTimer = setTimeout(() => {
    fetchSuggestions(value);
  }, DEBOUNCE_MS);
});
