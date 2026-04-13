import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors',
  {
    variants: {
      variant: {
        default:     'bg-primary/15 text-indigo-300 border border-primary/25',
        secondary:   'bg-white/[0.07] text-slate-300 border border-white/10',
        destructive: 'bg-red-500/15 text-red-400 border border-red-500/25',
        outline:     'border border-white/15 text-slate-300',
        success:     'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25',
        warning:     'bg-amber-500/15 text-amber-400 border border-amber-500/25',
        info:        'bg-blue-500/15 text-blue-400 border border-blue-500/25',
        critical:    'bg-red-500/20 text-red-300 border border-red-400/30 font-bold',
        high:        'bg-orange-500/15 text-orange-400 border border-orange-500/25',
        medium:      'bg-amber-500/15 text-amber-400 border border-amber-500/25',
        low:         'bg-emerald-500/12 text-emerald-400 border border-emerald-500/20',
      },
    },
    defaultVariants: { variant: 'default' },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}
