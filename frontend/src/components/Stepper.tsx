import { Check } from 'lucide-react';

interface StepperProps {
  currentStep: 'capture' | 'processing' | 'results';
}

export default function Stepper({ currentStep }: StepperProps) {
  const steps = [
    { id: 'capture', label: 'Take Selfie', index: 0 },
    { id: 'processing', label: 'Processing', index: 1 },
    { id: 'results', label: 'Your Photos', index: 2 },
  ];

  const getCurrentIndex = () => {
    return steps.find(s => s.id === currentStep)?.index || 0;
  };

  const currentIndex = getCurrentIndex();

  return (
    <div className="w-full max-w-lg mx-auto mb-10 px-4">
      <div className="flex items-center justify-between relative">
        {/* Background Line */}
        <div className="absolute left-0 right-0 top-4 h-[1px] bg-neutral-200 z-0" />
        
        {/* Progress Line */}
        <div 
          className="absolute left-0 top-4 h-[1px] bg-[var(--color-brand)] z-0 transition-all duration-500 ease-in-out" 
          style={{ width: `${(currentIndex / (steps.length - 1)) * 100}%` }}
        />

        {steps.map((step, i) => {
          const isCompleted = i < currentIndex;
          const isCurrent = i === currentIndex;
          
          return (
            <div key={step.id} className="relative z-10 flex flex-col items-center">
              <div 
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-colors duration-300
                  ${isCompleted ? 'bg-[var(--color-brand)] text-white' : 
                    isCurrent ? 'bg-white border-2 border-[var(--color-brand)] text-[var(--color-brand)]' : 
                    'bg-white border border-neutral-300 text-neutral-400'}`}
              >
                {isCompleted ? <Check className="w-4 h-4" /> : (i + 1)}
              </div>
              <span 
                className={`mt-2 text-[10px] sm:text-xs uppercase tracking-wider font-medium transition-colors duration-300
                  ${isCurrent || isCompleted ? 'text-neutral-800' : 'text-neutral-400'}`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
