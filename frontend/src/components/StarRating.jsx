export default function StarRating({ value, onChange, size = 'md' }) {
  const sizes = {
    sm: 'text-xl gap-1',
    md: 'text-3xl gap-1.5',
    lg: 'text-4xl gap-2',
  }

  return (
    <div className={`flex ${sizes[size]}`} role="radiogroup" aria-label="Star rating">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          aria-label={`${star} star${star > 1 ? 's' : ''}`}
          className={`transition-transform duration-100 hover:scale-110 active:scale-95 focus:outline-none
            ${star <= (value || 0) ? 'opacity-100' : 'opacity-25 hover:opacity-60'}`}
        >
          ★
        </button>
      ))}
    </div>
  )
}
