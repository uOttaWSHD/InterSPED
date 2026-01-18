"use client";

import { 
  LayoutDashboard, 
  PlayCircle, 
  History, 
  Settings, 
  LogOut,
  User as UserIcon,
  Plus
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";

export default function Dashboard() {
  const router = useRouter();

  const handleLogout = () => {
    router.push("/");
  };

  return (
    <div className="min-h-screen bg-[hsl(var(--background))] flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-white/5 bg-black/20 flex flex-col">
        <div className="p-6">
          <div className="flex items-center gap-2 mb-8">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <LayoutDashboard className="text-primary-foreground w-5 h-5" />
            </div>
            <span className="text-xl font-bold tracking-tight">Intersped</span>
          </div>

          <nav className="space-y-1">
            {[
              { icon: <LayoutDashboard className="w-4 h-4" />, label: "Overview", active: true },
              { icon: <History className="w-4 h-4" />, label: "Interview History" },
              { icon: <Settings className="w-4 h-4" />, label: "Settings" },
            ].map((item, i) => (
              <button
                key={i}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                  item.active 
                  ? "bg-primary/10 text-primary" 
                  : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
                }`}
              >
                {item.icon}
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="mt-auto p-6 border-t border-white/5">
          <button 
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8">
        <header className="flex items-center justify-between mb-12">
          <div>
            <h1 className="text-3xl font-bold mb-2">Welcome back, User</h1>
            <p className="text-muted-foreground text-sm">You have no interviews scheduled today.</p>
          </div>
          <div className="flex items-center gap-4">
             <Button variant="outline" className="bg-white/5 border-white/10">
               <UserIcon className="w-4 h-4 mr-2" />
               Profile
             </Button>
              <Button className="glow-primary" onClick={() => router.push("/interview")}>
                <Plus className="w-4 h-4 mr-2" />
                New Session
              </Button>
          </div>
        </header>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {[
            { label: "Total Sessions", value: "12" },
            { label: "Avg. Score", value: "84%" },
            { label: "Next Milestone", value: "Senior Dev Prep" },
          ].map((stat, i) => (
            <div key={i} className="glass-card p-6 rounded-2xl">
              <p className="text-sm text-muted-foreground mb-1">{stat.label}</p>
              <p className="text-2xl font-bold">{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Action Card */}
        <div className="relative glass-card p-8 md:p-12 rounded-[2rem] overflow-hidden group">
          <div className="absolute top-0 right-0 w-64 h-64 bg-primary/20 rounded-full blur-[80px] -mr-32 -mt-32 transition-transform group-hover:scale-110" />
          
          <div className="relative z-10 max-w-lg">
            <h2 className="text-2xl font-bold mb-4">Start your next mock interview</h2>
            <p className="text-muted-foreground mb-8">
              Pick a company and a job role, and our AI will generate a tailored interview session for you.
            </p>
            <Button size="lg" className="h-12 px-8 font-semibold" onClick={() => router.push("/interview")}>
              <PlayCircle className="w-5 h-5 mr-2" />
              Start Session
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
