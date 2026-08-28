export function TermsOfService() {
  return (
    <div className="flex flex-col min-h-screen bg-[#060c18] text-white p-8 font-sans">
      <div className="max-w-3xl mx-auto w-full bg-white/5 rounded-xl border border-white/10 p-8 shadow-xl mt-12">
        <h1 className="text-3xl font-bold mb-6 text-purple-400">Terms of Service</h1>
        <div className="space-y-4 text-gray-300 leading-relaxed">
          <p>By using Jarvis, you agree to these terms of service.</p>
          <h2 className="text-xl font-semibold text-white mt-6">Usage</h2>
          <p>This software is provided "as is", without warranty of any kind. You are responsible for any actions taken by the AI assistant on your behalf.</p>
          <h2 className="text-xl font-semibold text-white mt-6">Account Connectivity</h2>
          <p>You may choose to connect third-party accounts (like Google Workspace). You are responsible for ensuring that your use of these services complies with their respective terms of service.</p>
        </div>
      </div>
    </div>
  );
}
