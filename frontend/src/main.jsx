import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

const themeStorageKey = "finwrapped_theme"

function applyStoredTheme() {
  let storedTheme = "dark"

  try {
    storedTheme = window.localStorage.getItem(themeStorageKey) === "light" ? "light" : "dark"
  } catch {
    storedTheme = "dark"
  }

  document.body.classList.remove("dark", "light")
  document.body.classList.add(storedTheme)
  document.body.dataset.theme = storedTheme
  document.documentElement.style.colorScheme = storedTheme
}

applyStoredTheme()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
