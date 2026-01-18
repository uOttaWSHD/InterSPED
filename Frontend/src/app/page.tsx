"use client";

import { motion } from "framer-motion";
import { 
  Terminal, 
  MessageSquare, 
  Sparkles, 
  ChevronRight, 
  Github,
  Code2,
  BarChart3
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { useRouter } from "next/navigation";

export default function Landing() {
  const { login, isAuthenticated } = useAuth();
  const router = useRouter();

  const handleCTA = () => {
    if (isAuthenticated) {
      router.push("/dashboard");
    } else {
      login();
    }
  };

  return (
    <div className="min-h-screen bg-[hsl(var(--background))] overflow-x-hidden">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-background/80 backdrop-blur-md">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Terminal className="text-primary-foreground w-5 h-5" />
            </div>
            <span className="text-xl font-bold tracking-tight">Intersped</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
            <a href="#features" className="hover:text-primary transition-colors">Features</a>
            <a href="#about" className="hover:text-primary transition-colors">For Students</a>
            <Button variant="ghost" onClick={handleCTA}>
              {isAuthenticated ? "Dashboard" : "Login"}
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 md:pt-48 md:pb-32">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-primary/20 rounded-full blur-[120px] opacity-50" />
        </div>

        <div className="container mx-auto px-6 relative z-10 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-primary mb-6">
              <Sparkles className="w-3 h-3" />
              Built for CS Students by CS Students
            </div>
            <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8">
              Ace the <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent">Technical Round</span>
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
              Stop guessing if you're ready. Practice LeetCode-style technicals and behavioral loops with Intersped's real-time AI feedback.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button size="lg" className="h-14 px-8 text-lg font-semibold glow-primary" onClick={handleCTA}>
                Get Started with Discord
                <ChevronRight className="ml-2 w-5 h-5" />
              </Button>
              <Button size="lg" variant="outline" className="h-14 px-8 text-lg font-semibold bg-white/5 border-white/10">
                <Github className="mr-2 w-5 h-5" />
                Star on GitHub
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 bg-white/[0.02]">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold mb-4">Master Your Workflow</h2>
            <p className="text-muted-foreground">Everything you need to secure that summer internship or new grad role.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                icon: <Code2 className="w-8 h-8 text-primary" />,
                title: "Live Coding Sandbox",
                desc: "Solve algorithmic challenges in a real-time editor while the AI monitors your problem-solving approach."
              },
              {
                icon: <MessageSquare className="w-8 h-8 text-accent" />,
                title: "Behavioral Clarity",
                desc: "Get instant feedback on your 'STAR' method responses, eye contact, and vocal confidence."
              },
              {
                icon: <BarChart3 className="w-8 h-8 text-primary" />,
                title: "Post-Interview Audit",
                desc: "Deep-dive analysis into your performance with specific improvement points for your next round."
              }
            ].map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="glass-card p-8 rounded-2xl hover:bg-white/[0.07] transition-all group"
              >
                <div className="mb-6 group-hover:scale-110 transition-transform duration-300">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed">
                  {feature.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24">
        <div className="container mx-auto px-6">
          <div className="relative glass-card p-12 md:p-20 rounded-[3rem] text-center overflow-hidden">
             <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-[80px]" />
             <div className="absolute bottom-0 left-0 w-64 h-64 bg-accent/10 rounded-full blur-[80px]" />
             
             <h2 className="text-4xl md:text-5xl font-bold mb-8">Ready to secure the bag?</h2>
             <p className="text-lg text-muted-foreground mb-10 max-w-xl mx-auto">
               Join hundreds of CS students practicing with Intersped. Your next offer letter is one mock interview away.
             </p>
             <Button size="lg" className="h-14 px-12 text-lg font-bold" onClick={handleCTA}>
               Sign Up Now
             </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-white/5 text-center text-sm text-muted-foreground">
        <div className="container mx-auto px-6">
          <p>© 2026 Intersped. Built for the future of tech recruitment.</p>
        </div>
      </footer>
    </div>
  );
}
