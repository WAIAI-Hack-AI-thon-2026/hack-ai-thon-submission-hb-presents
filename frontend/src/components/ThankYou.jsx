export default function ThankYou({ onReset }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center space-y-6">
      <div className="w-20 h-20 rounded-full bg-brand-50 flex items-center justify-center text-4xl shadow-inner">
        ✅
      </div>

      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">All done!</h2>
        <p className="text-gray-500 text-sm max-w-xs mx-auto">
          Your feedback has been submitted. The property team will review it — thank you for helping improve future stays.
        </p>
      </div>

      <div className="flex flex-col items-center gap-1 text-sm text-gray-400">
        <p>Powered by</p>
        <p className="font-semibold text-brand-700">Ask What Matters · HB Presents</p>
        <p className="text-xs">Wharton Hack-AI-thon 2026</p>
      </div>

      <button
        type="button"
        onClick={onReset}
        className="btn-secondary mt-4"
      >
        ← Try another review
      </button>
    </div>
  )
}
