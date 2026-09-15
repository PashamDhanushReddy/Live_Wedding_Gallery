import { User, Sliders, Lock, Cloud, Bell, Camera } from "lucide-react";
import { useState } from "react";

export default function AdminSettings() {
  const [activeTab, setActiveTab] = useState("Profile");

  const tabs = [
    { name: "Profile", icon: User },
    { name: "Preferences", icon: Sliders },
    { name: "Privacy & Security", icon: Lock },
    { name: "Cloudinary", icon: Cloud },
    { name: "Notifications", icon: Bell },
  ];

  return (
    <div className="space-y-6 max-w-[1200px] mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 bg-white p-6 rounded-2xl shadow-sm border border-border">
        <div className="p-3 bg-primary/10 text-primary rounded-xl">
          <SettingsIcon className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-2xl font-serif text-foreground">Settings</h1>
          <p className="text-muted-foreground text-sm">Manage your profile, preferences, privacy, and account settings.</p>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar */}
        <div className="w-full lg:w-64 shrink-0 bg-white rounded-2xl shadow-sm border border-border p-4">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.name;
              const Icon = tab.icon;
              return (
                <button
                  key={tab.name}
                  onClick={() => setActiveTab(tab.name)}
                  className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                    isActive 
                      ? "bg-primary/10 text-primary" 
                      : "text-foreground hover:bg-secondary"
                  }`}
                >
                  <span className="flex items-center gap-3">
                    <Icon className={`w-5 h-5 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
                    {tab.name}
                  </span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 space-y-6">
          {activeTab === "Profile" && (
            <>
              {/* Profile Information */}
              <div className="bg-white rounded-2xl shadow-sm border border-border overflow-hidden">
                <div className="p-6 border-b border-border flex items-center gap-3">
                  <User className="w-5 h-5 text-muted-foreground" />
                  <h2 className="text-lg font-medium text-foreground">Profile Information</h2>
                </div>
                <div className="p-6">
                  <p className="text-sm text-muted-foreground mb-6">Update your personal information and profile picture.</p>
                  
                  <div className="flex flex-col sm:flex-row gap-8">
                    <div className="relative w-24 h-24 rounded-full bg-secondary shrink-0">
                      <div className="absolute inset-0 rounded-full overflow-hidden flex items-center justify-center font-bold text-2xl text-primary">
                        SR
                      </div>
                      <button className="absolute bottom-0 right-0 p-1.5 bg-foreground text-background rounded-full hover:bg-foreground/90">
                        <Camera className="w-4 h-4" />
                      </button>
                    </div>
                    
                    <div className="flex-1 space-y-4">
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Full Name</label>
                        <input type="text" defaultValue="Sandeep Reddy" className="w-full px-4 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary" />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Email Address</label>
                        <input type="email" defaultValue="sandeepreddy@example.com" className="w-full px-4 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary" />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Phone Number</label>
                        <input type="tel" defaultValue="+91 98765 43210" className="w-full px-4 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary" />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Role</label>
                        <input type="text" defaultValue="Admin" disabled className="w-full px-4 py-2 bg-secondary/50 border border-border rounded-lg text-sm text-muted-foreground cursor-not-allowed" />
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-8 flex justify-end">
                    <button className="bg-primary text-primary-foreground px-6 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors">
                      Save Changes
                    </button>
                  </div>
                </div>
              </div>

              {/* Change Password */}
              <div className="bg-white rounded-2xl shadow-sm border border-border overflow-hidden">
                <div className="p-6 border-b border-border flex items-center gap-3">
                  <Lock className="w-5 h-5 text-muted-foreground" />
                  <h2 className="text-lg font-medium text-foreground">Change Password</h2>
                </div>
                <div className="p-6">
                  <p className="text-sm text-muted-foreground mb-6">Update your password to keep your account secure.</p>
                  
                  <div className="space-y-4 max-w-lg">
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-foreground">Current Password</label>
                      <input type="password" placeholder="Enter current password" className="w-full px-4 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary" />
                    </div>
                    <div className="flex gap-4">
                      <div className="space-y-2 flex-1">
                        <label className="text-sm font-medium text-foreground">New Password</label>
                        <input type="password" placeholder="Enter new password" className="w-full px-4 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary" />
                      </div>
                      <div className="space-y-2 flex-1">
                        <label className="text-sm font-medium text-foreground">Confirm New Password</label>
                        <input type="password" placeholder="Confirm new password" className="w-full px-4 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary" />
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-8 flex justify-end">
                    <button className="bg-primary text-primary-foreground px-6 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors">
                      Save Password
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}

          {activeTab !== "Profile" && (
            <div className="bg-white rounded-2xl shadow-sm border border-border p-12 text-center">
              <div className="w-16 h-16 bg-secondary rounded-full flex items-center justify-center mx-auto mb-4 text-muted-foreground">
                <Sliders className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-medium text-foreground mb-2">{activeTab} Settings</h2>
              <p className="text-muted-foreground">This section is currently under construction.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SettingsIcon(props: any) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path>
      <circle cx="12" cy="12" r="3"></circle>
    </svg>
  );
}
