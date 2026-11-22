import { useEffect, useRef, useState } from 'react';
import { cn } from '@utils/cn';

interface WaveformProps {
  isActive: boolean;
  audioLevel?: number;
  barCount?: number;
  className?: string;
}

export function Waveform({ isActive, audioLevel = 0, barCount = 16, className }: WaveformProps) {
  const [bars, setBars] = useState<number[]>(Array(barCount).fill(0.1));
  const animationRef = useRef<number>();
  const audioLevelRef = useRef(audioLevel);

  audioLevelRef.current = audioLevel;

  useEffect(() => {
    if (!isActive) {
      setBars(prev => prev.map(() => 0.1));
      return;
    }

    const animate = () => {
      setBars(prev => prev.map((_, i) => {
        const baseHeight = 0.1 + Math.random() * 0.3;
        const levelInfluence = audioLevelRef.current * 0.6;
        const variation = Math.sin(Date.now() / 200 + i * 0.5) * 0.1;
        return Math.min(1, Math.max(0.1, baseHeight + levelInfluence + variation));
      }));
      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isActive, barCount]);

  return (
    <div
      className={cn('flex items-end gap-1 h-12', className)}
      role="img"
      aria-label={isActive ? 'Audio waveform visualization' : 'Audio waveform inactive'}
      aria-hidden={!isActive}
    >
      {bars.map((height, i) => (
        <div
          key={i}
          className={cn('waveform-bar flex-1 max-w-1 transition-all duration-[50ms] ease-out')}
          style={{
            height: `${height * 100}%`,
            animationDelay: `${i * 30}ms`,
          }}
          aria-hidden="true"
        />
      ))}
    </div>
  );
}

interface CircularWaveformProps {
  isActive: boolean;
  size?: number;
  className?: string;
}

export function CircularWaveform({ isActive, size = 80, className }: CircularWaveformProps) {
  const [radius, setRadius] = useState(0);
  const animationRef = useRef<number>();

  useEffect(() => {
    if (!isActive) {
      setRadius(0);
      return;
    }

    let startTime = Date.now();

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = (elapsed % 2000) / 2000;
      const newRadius = size * 0.3 + size * 0.4 * Math.sin(progress * Math.PI * 2);
      setRadius(Math.max(0, newRadius));
      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isActive, size]);

  return (
    <div
      className={cn('relative flex items-center justify-center', className)}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} fill="none">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={size / 2 - 2}
          stroke="currentColor"
          strokeWidth="2"
          opacity={0.15}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          opacity={0.6}
          style={{ filter: 'drop-shadow(0 0 4px currentColor)' }}
        />
      </svg>
    </div>
  );
}