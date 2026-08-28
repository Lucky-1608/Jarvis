export function PrivacyPolicy() {
  return (
    <div className="flex flex-col min-h-screen bg-[#060c18] text-white p-8 font-sans">
      <div className="max-w-3xl mx-auto w-full bg-white/5 rounded-xl border border-white/10 p-8 shadow-xl mt-12">
        <h1 className="text-3xl font-bold mb-6 text-purple-400">Privacy Policy</h1>
        <div className="space-y-4 text-gray-300 leading-relaxed">
          <p>This is a personal, local AI assistant (Jarvis). It does not collect or share data with any external third-parties other than the services you explicitly connect (like Google or Notion) to function properly.</p>
          <h2 className="text-xl font-semibold text-white mt-6">Data Collection & Usage</h2>
          <p>Any data processed by this application remains under your control and is processed solely to provide the AI assistant's functionality. The app only accesses the scopes you authorize for automation and briefing purposes.</p>
          <h2 className="text-xl font-semibold text-white mt-6">Third-Party Services</h2>
          <p>We use OAuth to authenticate with third-party services. Your authentication tokens are stored securely in your private database and are never transmitted to unauthorized servers.</p>
        </div>
      </div>
    </div>
  );
}
