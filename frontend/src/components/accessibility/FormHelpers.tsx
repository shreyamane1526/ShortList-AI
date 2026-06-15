/**
 * Accessible form helper components:
 * - CharCounter: shows character/word count below a textarea
 * - FieldHelper: shows helper text below a field
 */

interface CharCounterProps {
  value: string
  maxChars?: number
  showWords?: boolean
}

export function CharCounter({ value, maxChars, showWords = false }: CharCounterProps) {
  const chars = value.length
  const words = value.trim() ? value.trim().split(/\s+/).length : 0
  const nearLimit = maxChars ? chars > maxChars * 0.85 : false
  const overLimit = maxChars ? chars > maxChars : false

  return (
    <p
      className="nd-char-counter"
      aria-live="polite"
      aria-atomic="true"
      style={{ color: overLimit ? '#DC2626' : nearLimit ? '#D97706' : undefined }}
    >
      {showWords && <span>{words} word{words !== 1 ? 's' : ''} · </span>}
      {maxChars ? (
        <span>
          {chars}/{maxChars} characters
          {overLimit && ' — over limit'}
        </span>
      ) : (
        <span>{chars} character{chars !== 1 ? 's' : ''}</span>
      )}
    </p>
  )
}

interface FieldHelperProps {
  id?: string
  children: React.ReactNode
}

export function FieldHelper({ id, children }: FieldHelperProps) {
  return (
    <p id={id} className="nd-helper-text" role="note">
      {children}
    </p>
  )
}
