import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import * as UI from './index';
import { Popover } from './index';

describe('ui barrel', () => {
  it('exports every primitive', () => {
    for (const name of ['Truncate','Surface','Card','Grid','ScrollRegion','Tag','RecordCell','Popover','Modal','ActionBar','Table','CeilingBadge','StatBar']) {
      expect(UI).toHaveProperty(name);
    }
  });
  it('a representative primitive mounts', () => {
    const { container } = render(<Popover open={false} anchor={<button>x</button>}>y</Popover>);
    expect(container).toBeTruthy();
  });
});
